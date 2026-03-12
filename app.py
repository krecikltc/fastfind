from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# Ścieżka do folderu z Twoimi plikami .txt i .json
FOLDER_Z_DANYMI = 'dane'

def szukaj_w_plikach(szukany_user):
    """
    Funkcja przeszukuje pliki .txt (format: Nazwa:ip) i .json w poszukiwaniu podanej nazwy użytkownika.
    """
    znalezione_wyniki = []
    szukany_user_lower = szukany_user.lower()

    try:
        for nazwa_pliku in os.listdir(FOLDER_Z_DANYMI):
            sciezka_pliku = os.path.join(FOLDER_Z_DANYMI, nazwa_pliku)

            if not os.path.isfile(sciezka_pliku):
                continue

            # --- OBSŁUGA PLIKU .txt (TWOJ FORMAT: Nazwa:ip) ---
            if nazwa_pliku.endswith('.txt'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        for nr_linii, linia in enumerate(f, 1):
                            linia = linia.strip()
                            if not linia:  # pomijamy puste linie
                                continue
                                
                            # Sprawdzamy, czy linia zawiera szukanego użytkownika
                            if szukany_user_lower in linia.lower():
                                # Próba sparsowania formatu "Nazwa:ip"
                                if ':' in linia:
                                    czesci = linia.split(':', 1)  # dzielimy tylko przy pierwszym dwukropku
                                    nazwa = czesci[0].strip()
                                    ip = czesci[1].strip() if len(czesci) > 1 else ""
                                    
                                    znalezione_wyniki.append({
                                        "plik": nazwa_pliku,
                                        "typ": "txt",
                                        "linia": nr_linii,
                                        "nick": nazwa,
                                        "ip": ip,
                                        "czas": None  # brak czasu w Twoim formacie
                                    })
                                else:
                                    # Jeśli format inny niż oczekiwany
                                    znalezione_wyniki.append({
                                        "plik": nazwa_pliku,
                                        "typ": "txt",
                                        "linia": nr_linii,
                                        "surowe_dane": linia,
                                        "uwaga": "Nieprawidłowy format (brak ':')"
                                    })
                except Exception as e:
                    print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

            # --- OBSŁUGA PLIKU .json (bez zmian) ---
            elif nazwa_pliku.endswith('.json'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        dane_json = json.load(f)
                        if isinstance(dane_json, list):
                            for index, element in enumerate(dane_json):
                                if szukany_user_lower in str(element).lower():
                                    znalezione_wyniki.append({
                                        "plik": nazwa_pliku,
                                        "typ": "json",
                                        "indeks": index,
                                        "znaleziono_w_obiekcie": element
                                    })
                except json.JSONDecodeError:
                    print(f"Błąd parsowania JSON w pliku {nazwa_pliku}")
                except Exception as e:
                    print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

    except Exception as e:
        print(f"Błąd dostępu do folderu: {e}")

    return znalezione_wyniki

@app.route('/free/search', methods=['GET'])
def search():
    # 1. Pobierz parametr 'user' z zapytania (np. /free/search?user=test)
    user_to_find = request.args.get('user')

    # 2. Walidacja - czy parametr istnieje?
    if not user_to_find:
        return jsonify({"error": "Brak wymaganego parametru 'user'"}), 400

    # 3. Wykonaj wyszukiwanie w plikach
    wyniki = szukaj_w_plikach(user_to_find)

    # 4. Przygotuj odpowiedź
    odpowiedz = {
        "query": user_to_find,
        "timestamp": datetime.now().isoformat(),
        "results_count": len(wyniki),
        "results": wyniki
    }

    # 5. Zwróć dane w formacie JSON
    return jsonify(odpowiedz)

if __name__ == '__main__':
    # Ten fragment jest używany tylko podczas lokalnego testowania.
    # Na Renderze serwerem startowym będzie Gunicorn.
    app.run(debug=True, host='0.0.0.0', port=5000)
