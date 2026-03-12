from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# Ścieżka do folderu z Twoimi plikami .txt i .json
FOLDER_Z_DANYMI = 'dane'

def szukaj_w_plikach(szukany_user):
    """
    Funkcja przeszukuje pliki .txt i .json w poszukiwaniu podanej nazwy użytkownika.
    Zwraca listę słowników ze znaleziskami.
    """
    znalezione_wyniki = []
    szukany_user_lower = szukany_user.lower()  # Dla wyszukiwania bez względu na wielkość liter

    try:
        # Iterujemy przez wszystkie pliki w folderze 'dane'
        for nazwa_pliku in os.listdir(FOLDER_Z_DANYMI):
            sciezka_pliku = os.path.join(FOLDER_Z_DANYMI, nazwa_pliku)

            # Pomijamy podfoldery, interesują nas tylko pliki
            if not os.path.isfile(sciezka_pliku):
                continue

            # --- OBSŁUGA PLIKU .txt ---
            if nazwa_pliku.endswith('.txt'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        for nr_linii, linia in enumerate(f, 1):
                            # Sprawdzamy, czy szukany user (małymi literami) jest w linii
                            if szukany_user_lower in linia.lower():
                                # Przykład parsowania linii (zakładamy format: nick, ip, czas)
                                czesci = linia.strip().split(',')
                                if len(czesci) >= 3:
                                    znalezione_wyniki.append({
                                        "plik": nazwa_pliku,
                                        "typ": "txt",
                                        "linia": nr_linii,
                                        "nick": czesci[0].strip(),
                                        "ip": czesci[1].strip(),
                                        "czas": czesci[2].strip()
                                    })
                                else:
                                    # Jeśli format inny, zwracamy surową linię
                                    znalezione_wyniki.append({
                                        "plik": nazwa_pliku,
                                        "typ": "txt",
                                        "linia": nr_linii,
                                        "surowe_dane": linia.strip()
                                    })
                except Exception as e:
                    print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

            # --- OBSŁUGA PLIKU .json ---
            elif nazwa_pliku.endswith('.json'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        dane_json = json.load(f)  # Zakładamy, że plik JSON to lista obiektów

                        # Sprawdzamy, czy dane_json to lista (np. [{"user": "test", "ip": "..."}, ...])
                        if isinstance(dane_json, list):
                            for index, element in enumerate(dane_json):
                                # Przeszukujemy wartości w każdym elemencie JSON (słowniku)
                                # To jest prostsze podejście: szukamy w wartościach (jako string)
                                if szukany_user_lower in str(element).lower():
                                    # Dodajemy cały element jako znalezisko
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