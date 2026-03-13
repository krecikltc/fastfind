from flask import Flask, request, jsonify
import os
import json
import time
from datetime import datetime

app = Flask(__name__)

# Ścieżka do folderu z Twoimi plikami .txt i .json
FOLDER_Z_DANYMI = 'dane'

def szukaj_w_plikach(szukany_user):
    """
    Funkcja przeszukuje pliki .txt (format: Nazwa:ip) i .json.
    Zwraca MAX 1 wynik z każdego pliku (pierwszy znaleziony).
    """
    # UŻYJEMY SŁOWNIKA, ŻEBY GRUPOWAĆ WYNIKI PO NAZWIE PLIKU
    wyniki_wedlug_plikow = {}
    szukany_user_lower = szukany_user.lower()

    try:
        for nazwa_pliku in os.listdir(FOLDER_Z_DANYMI):
            sciezka_pliku = os.path.join(FOLDER_Z_DANYMI, nazwa_pliku)

            if not os.path.isfile(sciezka_pliku):
                continue

            # --- OBSŁUGA PLIKU .txt ---
            if nazwa_pliku.endswith('.txt'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        for linia in f:
                            linia = linia.strip()
                            if not linia:
                                continue
                                
                            if szukany_user_lower in linia.lower():
                                if ':' in linia:
                                    czesci = linia.split(':', 1)
                                    nazwa = czesci[0].strip()
                                    ip = czesci[1].strip() if len(czesci) > 1 else ""
                                    
                                    # ZAPISUJEMY TYLKO PIERWSZY WYNIK Z TEGO PLIKU
                                    if nazwa_pliku not in wyniki_wedlug_plikow:
                                        wyniki_wedlug_plikow[nazwa_pliku] = {
                                            "ip": ip,
                                            "nick": nazwa,
                                            "plik": nazwa_pliku
                                        }
                                        # PO ZNALEZIENIU PIERWSZEGO WYNIKU PRZERYWAMY SZUKANIE W TYM PLIKU
                                        break
                                else:
                                    if nazwa_pliku not in wyniki_wedlug_plikow:
                                        wyniki_wedlug_plikow[nazwa_pliku] = {
                                            "ip": "",
                                            "nick": linia,
                                            "plik": nazwa_pliku
                                        }
                                        break
                except Exception as e:
                    print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

            # --- OBSŁUGA PLIKU .json ---
            elif nazwa_pliku.endswith('.json'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        dane_json = json.load(f)
                        if isinstance(dane_json, list):
                            for element in dane_json:
                                if szukany_user_lower in str(element).lower():
                                    # ZAPISUJEMY TYLKO PIERWSZY WYNIK Z TEGO PLIKU
                                    if nazwa_pliku not in wyniki_wedlug_plikow:
                                        if isinstance(element, dict):
                                            wyniki_wedlug_plikow[nazwa_pliku] = {
                                                "ip": element.get('ip', ''),
                                                "nick": element.get('nick', str(element)),
                                                "plik": nazwa_pliku
                                            }
                                        else:
                                            wyniki_wedlug_plikow[nazwa_pliku] = {
                                                "ip": "",
                                                "nick": str(element),
                                                "plik": nazwa_pliku
                                            }
                                        # PO ZNALEZIENIU PIERWSZEGO WYNIKU PRZERYWAMY SZUKANIE W TYM PLIKU
                                        break
                except json.JSONDecodeError:
                    print(f"Błąd parsowania JSON w pliku {nazwa_pliku}")
                except Exception as e:
                    print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

    except Exception as e:
        print(f"Błąd dostępu do folderu: {e}")

    # SŁOWNIK ZAMIENIAMY NA LISTĘ (bo słownik był tylko po to, żeby uniknąć duplikatów z tego samego pliku)
    return list(wyniki_wedlug_plikow.values())

@app.route('/free/search', methods=['GET'])
def search():
    # START POMIARU CZASU
    start_time = time.time()
    
    # 1. Pobierz parametr 'user' z zapytania
    user_to_find = request.args.get('user')

    # 2. Walidacja
    if not user_to_find:
        return jsonify({"error": "Brak wymaganego parametru 'user'"}), 400

    # 3. Wykonaj wyszukiwanie w plikach (MAX 1 WYNIK Z PLIKU)
    wyniki_bez_czasu = szukaj_w_plikach(user_to_find)
    
    # KONIEC POMIARU CZASU
    end_time = time.time()
    czas_wykonania = round(end_time - start_time, 3)

    # 4. DODAJEMY CZAS DO KAŻDEGO WYNIKU
    wyniki_z_czasem = []
    for wynik in wyniki_bez_czasu:
        wynik_z_czasem = {
            "czas": czas_wykonania,
            "ip": wynik["ip"],
            "nick": wynik["nick"],
            "plik": wynik["plik"]
        }
        wyniki_z_czasem.append(wynik_z_czasem)

    # 5. Przygotuj odpowiedź
    odpowiedz = {
        "results_count": len(wyniki_z_czasem),
        "results": wyniki_z_czasem
    }

    return jsonify(odpowiedz)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
