from flask import Flask, request, jsonify, render_template_string, redirect
import os
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import secrets

load_dotenv()
app = Flask(__name__)

# ============================================
# KONFIGURACJA SUPABASE
# ============================================
# Te dane weźmiesz z Supabase za chwilę!
DB_HOST = os.getenv('SUPABASE_HOST', 'aws-0-eu-central-1.pooler.supabase.com')
DB_USER = os.getenv('SUPABASE_USER', 'postgres.twojprojekt')  # Zmienisz później
DB_PASS = os.getenv('SUPABASE_PASS', 'twoje-haslo')           # Zmienisz później
DB_NAME = os.getenv('SUPABASE_NAME', 'postgres')
DB_PORT = os.getenv('SUPABASE_PORT', '6543')

# Tworzymy połączenie z bazą
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ============================================
# MODEL KLIENTA (tabela w bazie)
# ============================================
class Client(Base):
    __tablename__ = 'klienci'
    
    owner = Column(String, primary_key=True)
    wazny_do = Column(DateTime, nullable=False)
    utworzono = Column(DateTime, default=datetime.now)
    dni = Column(Integer, default=1)
    discord = Column(String)
    
    def to_dict(self):
        return {
            'owner': self.owner,
            'wazny_do': self.wazny_do.isoformat(),
            'utworzono': self.utworzono.isoformat(),
            'dni': self.dni,
            'discord': self.discord
        }

# Tworzymy tabelę jeśli nie istnieje
Base.metadata.create_all(engine)

# ============================================
# FUNKCJE BAZODANOWE
# ============================================
def wczytaj_klientow():
    """Wczytuje wszystkich klientów z bazy"""
    session = SessionLocal()
    try:
        klienci = session.query(Client).all()
        return {k.owner: k.to_dict() for k in klienci}
    finally:
        session.close()

def zapisz_klienta(owner, discord, dni):
    """Dodaje nowego klienta do bazy"""
    session = SessionLocal()
    try:
        wazny_do = datetime.now().replace(hour=23, minute=59, second=59)
        wazny_do += timedelta(days=dni)
        
        client = Client(
            owner=owner,
            wazny_do=wazny_do,
            dni=dni,
            discord=discord
        )
        session.add(client)
        session.commit()
        return wazny_do
    finally:
        session.close()

def usun_klienta(owner):
    """Usuwa klienta z bazy"""
    session = SessionLocal()
    try:
        session.query(Client).filter(Client.owner == owner).delete()
        session.commit()
    finally:
        session.close()

def przedluz_klienta(owner, dni):
    """Przedłuża klienta w bazie"""
    session = SessionLocal()
    try:
        client = session.query(Client).filter(Client.owner == owner).first()
        if client:
            client.wazny_do = client.wazny_do + timedelta(days=dni)
            client.dni = client.dni + dni
            session.commit()
            return True
        return False
    finally:
        session.close()

def sprawdz_klienta(owner):
    """Sprawdza czy klient istnieje i ma ważny dostęp"""
    session = SessionLocal()
    try:
        client = session.query(Client).filter(Client.owner == owner).first()
        if not client:
            return False, "Nieznany owner"
        
        if datetime.now() > client.wazny_do:
            return False, "Dostęp wygasł"
        
        return True, client.wazny_do
    finally:
        session.close()

# ============================================
# FUNKCJA WYSZUKIWANIA (bez zmian)
# ============================================
FOLDER_Z_DANYMI = 'dane'

def szukaj_w_plikach(szukany_user):
    """Zwraca MAX 1 wynik z każdego pliku"""
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
                    
            elif nazwa_pliku.endswith('.json'):
                try:
                    with open(sciezka_pliku, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if szukany_user_lower in str(item).lower():
                                    if nazwa_pliku not in wyniki_wedlug_plikow:
                                        if isinstance(item, dict):
                                            wyniki_wedlug_plikow[nazwa_pliku] = {
                                                "ip": item.get('ip', ''),
                                                "nick": item.get('nick', str(item)),
                                                "plik": nazwa_pliku
                                            }
                                        else:
                                            wyniki_wedlug_plikow[nazwa_pliku] = {
                                                "ip": "",
                                                "nick": str(item),
                                                "plik": nazwa_pliku
                                            }
                                        break
                except Exception as e:
                    print(f"Błąd JSON {nazwa_pliku}: {e}")
    except Exception as e:
        print(f"Błąd: {e}")

    return list(wyniki_wedlug_plikow.values())

# ============================================
# ENDPOINT API DLA KLIENTÓW
# ============================================
@app.route('/api/search', methods=['GET'])
def api_search():
    owner = request.args.get('owner')
    user = request.args.get('user')
    
    if not owner or not user:
        return jsonify({"error": "Brak owner lub user"}), 400
    
    status, info = sprawdz_klienta(owner)
    if not status:
        return jsonify({"error": info}), 403
    
    start = time.time()
    wyniki = szukaj_w_plikach(user)
    czas = round(time.time() - start, 3)
    
    wyniki_z_czasem = []
    for w in wyniki:
        wyniki_z_czasem.append({
            "czas": czas,
            "ip": w["ip"],
            "nick": w["nick"],
            "plik": w["plik"]
        })
    
    return jsonify({
        "owner": owner,
        "user": user,
        "results_count": len(wyniki_z_czasem),
        "results": wyniki_z_czasem
    })

# ============================================
# PANEL ADMINISTRATORA (ten sam HTML co wcześniej)
# ============================================
HASLO_ADMINA = "twoje-tajne-haslo-zmien-to!"  # <- ZMIEN!

PANEL_HTML = '''(TUTAJ WCALEJ TEN SAM HTML CO WCZEŚNIEJ - nie zmieniaj)'''

@app.route('/admin', methods=['GET'])
def admin_panel():
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Logowanie</title>
        <style>body{font-family:Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);height:100vh;display:flex;justify-content:center;align-items:center;}.login-box{background:white;padding:40px;border-radius:10px;width:300px;}input,button{width:100%;padding:12px;margin:10px 0;}</style>
        </head>
        <body><div class="login-box"><h2>Panel Admina</h2><form method="GET"><input type="password" name="auth" placeholder="Hasło" required><button type="submit">Zaloguj</button></form></div></body>
        </html>
        '''
    
    klienci = wczytaj_klientow()
    
    def datetime_filter(date_str):
        return datetime.fromisoformat(date_str)
    app.jinja_env.filters['datetime'] = datetime_filter
    
    return render_template_string(
        PANEL_HTML, 
        klienci=klienci, 
        now=datetime.now(),
        message=request.args.get('message'),
        message_type=request.args.get('message_type'),
        auth=auth
    )

@app.route('/admin/add', methods=['POST'])
def admin_add():
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    discord = request.form.get('discord')
    dni = int(request.form.get('dni', 7))
    
    if not owner or not discord:
        return redirect(f'/admin?auth={auth}&message=Brak wymaganych pól&message_type=error')
    
    try:
        wazny_do = zapisz_klienta(owner, discord, dni)
        return redirect(f'/admin?auth={auth}&message=Dodano {owner} (Discord: {discord})&message_type=success')
    except Exception as e:
        return redirect(f'/admin?auth={auth}&message=Błąd: {str(e)}&message_type=error')

@app.route('/admin/delete', methods=['POST'])
def admin_delete():
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    usun_klienta(owner)
    return redirect(f'/admin?auth={auth}&message=Usunięto {owner}&message_type=success')

@app.route('/admin/extend', methods=['POST'])
def admin_extend():
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    dni = int(request.form.get('dni', 7))
    
    if przedluz_klienta(owner, dni):
        return redirect(f'/admin?auth={auth}&message=Przedłużono {owner} o {dni} dni&message_type=success')
    else:
        return redirect(f'/admin?auth={auth}&message=Nie znaleziono {owner}&message_type=error')

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return jsonify({"error": "Brak dostępu"}), 403
    
    klienci = wczytaj_klientow()
    teraz = datetime.now()
    
    aktywni = 0
    wygasli = 0
    
    for dane in klienci.values():
        wazny_do = datetime.fromisoformat(dane['wazny_do'])
        if teraz <= wazny_do:
            aktywni += 1
        else:
            wygasli += 1
    
    pliki = 0
    if os.path.exists(FOLDER_Z_DANYMI):
        pliki = len([f for f in os.listdir(FOLDER_Z_DANYMI) if os.path.isfile(os.path.join(FOLDER_Z_DANYMI, f))])
    
    return jsonify({
        "aktywni": aktywni,
        "wygasli": wygasli,
        "pliki": pliki
    })

@app.route('/', methods=['GET'])
def home():
    return redirect('/admin')

if __name__ == '__main__':
    if not os.path.exists(FOLDER_Z_DANYMI):
        os.makedirs(FOLDER_Z_DANYMI)
    app.run(debug=True, host='0.0.0.0', port=5000)
