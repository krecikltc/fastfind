from flask import Flask, request, jsonify
import os
import json
import time
from datetime import datetime, timedelta

app = Flask(__name__)

FOLDER_Z_DANYMI = 'dane'
PLIK_Z_KLIENTAMI = 'klienci.json'
HASLO_ADMINA = "twoje-tajne-haslo"

# ============================================
# ZARZĄDZANIE KLIENTAMI (bez kluczy, tylko owner)
# ============================================

def wczytaj_klientow():
    """Wczytuje listę klientów i ich dat ważności"""
    if not os.path.exists(PLIK_Z_KLIENTAMI):
        return {}
    with open(PLIK_Z_KLIENTAMI, 'r', encoding='utf-8') as f:
        return json.load(f)

def zapisz_klientow(klienci):
    with open(PLIK_Z_KLIENTAMI, 'w', encoding='utf-8') as f:
        json.dump(klienci, f, indent=2)

def dodaj_klienta(owner, dni):
    """Dodaje nowego klienta z datą ważności"""
    klienci = wczytaj_klientow()
    
    # Oblicz datę ważności (do końca dnia)
    wazny_do = datetime.now().replace(hour=23, minute=59, second=59)
    wazny_do += timedelta(days=dni)
    
    klienci[owner] = {
        "wazny_do": wazny_do.isoformat(),
        "utworzono": datetime.now().isoformat(),
        "dni": dni
    }
    
    zapisz_klientow(klienci)
    return wazny_do

def sprawdz_klienta(owner):
    """Sprawdza czy klient istnieje i czy jego dostęp jest ważny"""
    klienci = wczytaj_klientow()
    
    if owner not in klienci:
        return False, "Nieznany owner"
    
    dane = klienci[owner]
    wazny_do = datetime.fromisoformat(dane['wazny_do'])
    
    if datetime.now() > wazny_do:
        return False, "Okres dostępu wygasł"
    
    return True, wazny_do

# ============================================
# WYSZUKIWANIE (bez zmian)
# ============================================

def szukaj_w_plikach(szukany_user):
    """Zwraca MAX 1 wynik z pliku"""
    wyniki_wedlug_plikow = {}
    szukany_user_lower = szukany_user.lower()

    try:
        for nazwa_pliku in os.listdir(FOLDER_Z_DANYMI):
            sciezka_pliku = os.path.join(FOLDER_Z_DANYMI, nazwa_pliku)
            if not os.path.isfile(sciezka_pliku):
                continue

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
                                    ip = czesci[1].strip()
                                    if nazwa_pliku not in wyniki_wedlug_plikow:
                                        wyniki_wedlug_plikow[nazwa_pliku] = {
                                            "ip": ip,
                                            "nick": nazwa,
                                            "plik": nazwa_pliku
                                        }
                                        break
                except Exception as e:
                    print(f"Błąd pliku {nazwa_pliku}: {e}")
    except Exception as e:
        print(f"Błąd: {e}")

    return list(wyniki_wedlug_plikow.values())

# ============================================
# ENDPOINTY
# ============================================

@app.route('/free/search', methods=['GET'])
def search():
    """
    GŁÓWNY ENDPOINT - klient podaje tylko owner i user
    https://twoja-domena.pl/free/search?owner=janek123&user=Janek
    """
    owner = request.args.get('owner')
    user = request.args.get('user')
    
    if not owner or not user:
        return jsonify({
            "error": "Brak wymaganych parametrów",
            "przyklad": "/free/search?owner=NAZWA&user=SZUKANY"
        }), 400
    
    # Sprawdź czy klient ma ważny dostęp
    status, info = sprawdz_klienta(owner)
    if not status:
        return jsonify({
            "error": "Brak dostępu",
            "powod": info,
            "kontakt": "Skontaktuj się z administratorem w celu przedłużenia"
        }), 403
    
    start = time.time()
    wyniki = szukaj_w_plikach(user)
    czas = round(time.time() - start, 3)
    
    # Formatuj wyniki
    wyniki_z_czasem = []
    for w in wyniki:
        wyniki_z_czasem.append({
            "czas": czas,
            "ip": w["ip"],
            "nick": w["nick"],
            "plik": w["plik"]
        })
    
    return jsonify({
        "query": user,
        "owner": owner,
        "wazny_do": info.isoformat() if not isinstance(info, str) else info,
        "results_count": len(wyniki_z_czasem),
        "results": wyniki_z_czasem
    })

# ============================================
# ENDPOINTY DLA ADMINA
# ============================================

@app.route('/admin/create', methods=['POST'])
def create_client():
    """Admin tworzy nowego klienta (tylko na podstawie owner)"""
    admin_pass = request.headers.get('X-Admin-Password')
    if admin_pass != HASLO_ADMINA:
        return jsonify({"error": "Brak uprawnień"}), 403
    
    data = request.json
    owner = data.get('owner')
    dni = data.get('dni', 1)  # domyślnie 1 dzień
    
    if not owner:
        return jsonify({"error": "Brak nazwy owner"}), 400
    
    wazny_do = dodaj_klienta(owner, dni)
    
    return jsonify({
        "sukces": True,
        "owner": owner,
        "wazny_do": wazny_do.isoformat(),
        "instrukcja_dla_klienta": f"https://fastfind.onrender.com/free/search?owner={owner}&user=Janek"
    })

@app.route('/admin/list', methods=['GET'])
def list_clients():
    """Admin widzi wszystkich klientów i ich status"""
    admin_pass = request.headers.get('X-Admin-Password')
    if admin_pass != HASLO_ADMINA:
        return jsonify({"error": "Brak uprawnień"}), 403
    
    klienci = wczytaj_klientow()
    teraz = datetime.now()
    
    lista = []
    for owner, dane in klienci.items():
        wazny_do = datetime.fromisoformat(dane['wazny_do'])
        aktywny = teraz <= wazny_do
        
        lista.append({
            "owner": owner,
            "aktywny": aktywny,
            "wazny_do": dane['wazny_do'],
            "utworzono": dane.get('utworzono', 'nieznane'),
            "dni": dane.get('dni', 1)
        })
    
    return jsonify({
        "klienci": lista,
        "liczba": len(lista)
    })

@app.route('/admin/extend/<owner>', methods=['POST'])
def extend_client(owner):
    """Admin przedłuża dostęp klienta"""
    admin_pass = request.headers.get('X-Admin-Password')
    if admin_pass != HASLO_ADMINA:
        return jsonify({"error": "Brak uprawnień"}), 403
    
    data = request.json
    dodatkowe_dni = data.get('dni', 1)
    
    klienci = wczytaj_klientow()
    if owner not in klienci:
        return jsonify({"error": "Nie ma takiego klienta"}), 404
    
    # Przedłuż datę
    stara_data = datetime.fromisoformat(klienci[owner]['wazny_do'])
    nowa_data = stara_data + timedelta(days=dodatkowe_dni)
    klienci[owner]['wazny_do'] = nowa_data.isoformat()
    klienci[owner]['dni'] = klienci[owner].get('dni', 1) + dodatkowe_dni
    
    zapisz_klientow(klienci)
    
    return jsonify({
        "sukces": True,
        "owner": owner,
        "nowa_data_waznosci": nowa_data.isoformat()
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "api": "FastFind",
        "wersja": "2.0 ",
        "dla_klientow": "/free/search?owner=TWOJA_NAZWA&user=SZUKANY",
        "jak_zdobyc_dostep": "Kontakt: discord.gg/aVe2Qce7"
    })

if __name__ == '__main__':
    # Przy starcie wyświetl info
    print("🚀 FastFind API z systemem owner (bez kluczy)")
    print("🔧 Panel admina:")
    print("   - POST /admin/create   (dodaj klienta)")
    print("   - GET  /admin/list     (lista klientów)")
    print("   - POST /admin/extend/NAZWA (przedłuż)")
    app.run(debug=True, host='0.0.0.0', port=5000)
