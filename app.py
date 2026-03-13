from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import os
import json
import time
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)

# Konfiguracja
FOLDER_Z_DANYMI = 'dane'
PLIK_Z_KLIENTAMI = 'klienci.json'
HASLO_ADMINA = "twoje-tajne-haslo-zmien-to!"  # <- ZMIEN TO!

# ============================================
# FUNKCJE POMOCNICZE
# ============================================

def wczytaj_klientow():
    """Wczytuje klientów z pliku JSON"""
    if not os.path.exists(PLIK_Z_KLIENTAMI):
        # Jeśli plik nie istnieje, utwórz pusty
        with open(PLIK_Z_KLIENTAMI, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(PLIK_Z_KLIENTAMI, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Jeśli błąd odczytu, zwróć pusty słownik
        return {}

def zapisz_klientow(klienci):
    """Zapisuje klientów do pliku JSON"""
    with open(PLIK_Z_KLIENTAMI, 'w', encoding='utf-8') as f:
        json.dump(klienci, f, indent=2, ensure_ascii=False)

def sprawdz_klienta(owner):
    """Sprawdza czy klient ma ważny dostęp"""
    klienci = wczytaj_klientow()
    
    if owner not in klienci:
        return False, "Nieznany owner"
    
    wazny_do = datetime.fromisoformat(klienci[owner]['wazny_do'])
    if datetime.now() > wazny_do:
        return False, "Dostęp wygasł"
    
    return True, wazny_do

# ============================================
# FUNKCJA WYSZUKIWANIA
# ============================================

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
    """Endpoint API używany przez klientów"""
    owner = request.args.get('owner')
    user = request.args.get('user')
    
    if not owner or not user:
        return jsonify({
            "error": "Brak wymaganych parametrów",
            "przyklad": "/api/search?owner=NAZWA&user=SZUKANY"
        }), 400
    
    # Sprawdź dostęp
    status, info = sprawdz_klienta(owner)
    if not status:
        return jsonify({
            "error": "Brak dostępu",
            "powod": info
        }), 403
    
    # Wykonaj wyszukiwanie
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
        "owner": owner,
        "user": user,
        "results_count": len(wyniki_z_czasem),
        "results": wyniki_z_czasem
    })

# ============================================
# PANEL ADMINISTRATORA
# ============================================

# Szablon HTML z CSS dla panelu admina
PANEL_HTML = '''
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FastFind API - Panel Admina</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Nagłówek */
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header h1 span {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 50px;
            font-size: 0.5em;
            margin-left: 15px;
        }
        
        .header .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-box {
            background: #f5f5f5;
            padding: 15px 25px;
            border-radius: 10px;
            flex: 1;
            text-align: center;
        }
        
        .stat-box .number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-box .label {
            color: #666;
            margin-top: 5px;
        }
        
        /* Grid dla formularza i listy */
        .admin-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        /* Karty */
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .card h2 i {
            color: #667eea;
            margin-right: 10px;
        }
        
        /* Formularze */
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .form-group input:focus, .form-group select:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            width: 100%;
            font-weight: 600;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .btn-small {
            padding: 8px 15px;
            font-size: 14px;
            width: auto;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #48bb78 0%, #2f855a 100%);
        }
        
        /* Tabela klientów */
        .clients-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .clients-table th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #555;
        }
        
        .clients-table td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .clients-table tr:hover {
            background: #f8f9fa;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-active {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .status-expired {
            background: #fed7d7;
            color: #742a2a;
        }
        
        /* Test API */
        .test-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-top: 30px;
        }
        
        .test-result {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }
        
        /* Alerty */
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateY(-10px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .alert-success {
            background: #c6f6d5;
            color: #22543d;
            border-left: 4px solid #48bb78;
        }
        
        .alert-error {
            background: #fed7d7;
            color: #742a2a;
            border-left: 4px solid #f56565;
        }
        
        /* Responsywność */
        @media (max-width: 768px) {
            .admin-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .stats {
                flex-direction: column;
            }
        }
        
        /* Loading */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Nagłówek z statystykami -->
        <div class="header">
            <h1>
                🔐 FastFind API - Panel Administratora
                <span>v2.0</span>
            </h1>
            <div class="stats" id="statsContainer">
                <div class="stat-box">
                    <div class="number" id="aktywniCount">0</div>
                    <div class="label">Aktywni klienci</div>
                </div>
                <div class="stat-box">
                    <div class="number" id="wygasliCount">0</div>
                    <div class="label">Wygasłe konta</div>
                </div>
                <div class="stat-box">
                    <div class="number" id="plikiCount">0</div>
                    <div class="label">Pliki do szukania</div>
                </div>
            </div>
        </div>
        
        <!-- Komunikaty -->
        {% if message %}
        <div class="alert alert-{{ message_type }}">
            {{ message }}
        </div>
        {% endif %}
        
        <!-- Grid: Dodawanie klienta + Szybkie akcje -->
        <div class="admin-grid">
            <!-- Dodawanie nowego klienta -->
            <div class="card">
                <h2>
                    <i>➕</i> Dodaj nowego klienta
                </h2>
                <form method="POST" action="/admin/add?auth={{ auth }}">
                    <div class="form-group">
                        <label>Nazwa klienta (owner):</label>
                        <input type="text" name="owner" required 
                               placeholder="np. janek123, firma_kowalski">
                    </div>
                    <div class="form-group">
                        <label>Discord klienta:</label>
                        <input type="text" name="discord" required 
                               placeholder="np. janek#1234 lub @janek">
                    </div>
                    <div class="form-group">
                        <label>Czas dostępu:</label>
                        <select name="dni">
                            <option value="1">1 dzień</option>
                            <option value="3">3 dni</option>
                            <option value="7" selected>7 dni</option>
                            <option value="14">14 dni</option>
                            <option value="30">30 dni</option>
                            <option value="90">90 dni</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">
                        🚀 Generuj dostęp
                    </button>
                </form>
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                    <h3>📋 Instrukcja dla klienta:</h3>
                    <p style="background: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace; margin-top: 10px;">
                        GET /api/search?owner=NAZWA&user=SZUKANY
                    </p>
                </div>
            </div>
            
            <!-- Szybkie akcje -->
            <div class="card">
                <h2>
                    <i>⚡</i> Szybkie akcje
                </h2>
                
                <div style="margin-bottom: 20px;">
                    <h3>Przedłuż klienta</h3>
                    <form method="POST" action="/admin/extend?auth={{ auth }}" style="display: flex; gap: 10px;">
                        <input type="text" name="owner" placeholder="Nazwa klienta" required style="flex: 2;">
                        <select name="dni" style="flex: 1;">
                            <option value="1">+1</option>
                            <option value="3">+3</option>
                            <option value="7">+7</option>
                            <option value="30">+30</option>
                        </select>
                        <button type="submit" class="btn-small btn-success">➕</button>
                    </form>
                </div>
                
                <div>
                    <h3>Test API (szybki podgląd)</h3>
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="testOwner" placeholder="owner" style="flex: 1;">
                        <input type="text" id="testUser" placeholder="user" style="flex: 1;">
                        <button onclick="testApi()" class="btn-small">🔍 Test</button>
                    </div>
                    <div id="testResult" class="test-result">
                        Tutaj pojawi się wynik testu...
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Lista klientów -->
        <div class="card" style="margin-top: 30px;">
            <h2>
                <i>📋</i> Lista klientów
            </h2>
            
            <table class="clients-table">
                <thead>
                    <tr>
                        <th>Owner</th>
                        <th>Discord</th>
                        <th>Ważny do</th>
                        <th>Status</th>
                        <th>Dni</th>
                        <th>Akcje</th>
                    </tr>
                </thead>
                <tbody>
                    {% for owner, dane in klienci.items() %}
                    {% set wazny_do = dane.wazny_do|datetime %}
                    {% set aktywny = wazny_do > now %}
                    <tr>
                        <td><strong>{{ owner }}</strong></td>
                        <td>{{ dane.discord }}</td>
                        <td>{{ dane.wazny_do[:10] }} {{ dane.wazny_do[11:16] }}</td>
                        <td>
                            {% if aktywny %}
                            <span class="status-badge status-active">✅ Aktywny</span>
                            {% else %}
                            <span class="status-badge status-expired">❌ Wygasł</span>
                            {% endif %}
                        </td>
                        <td>{{ dane.dni }} dni</td>
                        <td>
                            <form method="POST" action="/admin/delete?auth={{ auth }}" style="display: inline;">
                                <input type="hidden" name="owner" value="{{ owner }}">
                                <button type="submit" class="btn-small btn-danger" 
                                        onclick="return confirm('Na pewno usunąć?')">
                                    🗑️ Usuń
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            {% if not klienci %}
            <p style="text-align: center; color: #888; padding: 30px;">
                Brak klientów. Dodaj pierwszego klienta!
            </p>
            {% endif %}
        </div>
        
        <!-- Dokumentacja API -->
        <div class="test-section">
            <h2>📚 Dokumentacja API dla klientów</h2>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px;">
                <div>
                    <h3>Endpoint:</h3>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
GET https://{{ request.host }}/api/search
                    </pre>
                    
                    <h3 style="margin-top: 20px;">Parametry:</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li style="margin: 10px 0;"><code>owner</code> - nazwa klienta (wymagany)</li>
                        <li style="margin: 10px 0;"><code>user</code> - szukana nazwa (wymagany)</li>
                    </ul>
                </div>
                
                <div>
                    <h3>Przykład zapytania:</h3>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
https://{{ request.host }}/api/search?owner=janek123&user=Admin
                    </pre>
                    
                    <h3 style="margin-top: 20px;">Przykład odpowiedzi:</h3>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
{
  "owner": "janek123",
  "user": "Admin",
  "results_count": 1,
  "results": [
    {
      "czas": 0.023,
      "ip": "192.168.1.1",
      "nick": "Admin",
      "plik": "users.txt"
    }
  ]
}
                    </pre>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Funkcja do testowania API
        function testApi() {
            const owner = document.getElementById('testOwner').value;
            const user = document.getElementById('testUser').value;
            
            if (!owner || !user) {
                alert('Wpisz owner i user do testu!');
                return;
            }
            
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '<div class="loading"></div> Łączenie...';
            
            fetch(`/api/search?owner=${owner}&user=${user}`)
                .then(response => response.json())
                .then(data => {
                    resultDiv.innerHTML = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    resultDiv.innerHTML = 'Błąd: ' + error;
                });
        }
        
        // Funkcja do aktualizacji statystyk
        function updateStats() {
            const auth = "{{ auth }}";
            
            fetch(`/admin/stats?auth=${auth}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('aktywniCount').textContent = data.aktywni;
                    document.getElementById('wygasliCount').textContent = data.wygasli;
                    document.getElementById('plikiCount').textContent = data.pliki;
                })
                .catch(error => {
                    console.log('Błąd statystyk:', error);
                });
        }
        
        // Aktualizuj statystyki od razu i co 30 sekund
        updateStats();
        setInterval(updateStats, 30000);
    </script>
</body>
</html>
'''

@app.route('/admin', methods=['GET'])
def admin_panel():
    """Główny panel admina"""
    auth = request.args.get('auth')
    
    if auth != HASLO_ADMINA:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Logowanie</title>
            <style>
                body { 
                    font-family: Arial; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .login-box {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    width: 300px;
                }
                h2 {
                    color: #333;
                    margin-bottom: 20px;
                    text-align: center;
                }
                input {
                    width: 100%;
                    padding: 12px;
                    margin: 10px 0;
                    border: 2px solid #ddd;
                    border-radius: 5px;
                    font-size: 14px;
                }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                }
                button:hover {
                    background: #5a67d8;
                }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>🔐 Panel Admina</h2>
                <form method="GET">
                    <input type="password" name="auth" placeholder="Hasło" required>
                    <button type="submit">Zaloguj</button>
                </form>
            </div>
        </body>
        </html>
        '''
    
    klienci = wczytaj_klientow()
    
    # Dodaj filtr datetime do szablonu
    def datetime_filter(date_str):
        try:
            return datetime.fromisoformat(date_str)
        except:
            return datetime.now()
    
    app.jinja_env.filters['datetime'] = datetime_filter
    
    message = request.args.get('message')
    message_type = request.args.get('message_type')
    
    return render_template_string(
        PANEL_HTML, 
        klienci=klienci, 
        now=datetime.now(),
        message=message,
        message_type=message_type,
        auth=auth
    )

@app.route('/admin/add', methods=['POST'])
def admin_add():
    """Dodaje nowego klienta"""
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    discord = request.form.get('discord')
    dni = int(request.form.get('dni', 7))
    
    if not owner or not discord:
        return redirect(f'/admin?auth={auth}&message=Brak wymaganych pól&message_type=error')
    
    klienci = wczytaj_klientow()
    
    # Sprawdź czy owner już istnieje
    if owner in klienci:
        return redirect(f'/admin?auth={auth}&message=Klient {owner} już istnieje&message_type=error')
    
    wazny_do = datetime.now().replace(hour=23, minute=59, second=59)
    wazny_do += timedelta(days=dni)
    
    klienci[owner] = {
        "wazny_do": wazny_do.isoformat(),
        "utworzono": datetime.now().isoformat(),
        "dni": dni,
        "discord": discord
    }
    
    zapisz_klientow(klienci)
    
    return redirect(f'/admin?auth={auth}&message=Dodano klienta {owner} (Discord: {discord})&message_type=success')

@app.route('/admin/delete', methods=['POST'])
def admin_delete():
    """Usuwa klienta"""
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    klienci = wczytaj_klientow()
    
    if owner in klienci:
        discord = klienci[owner].get('discord', 'nieznany')
        del klienci[owner]
        zapisz_klientow(klienci)
        return redirect(f'/admin?auth={auth}&message=Usunięto {owner} (Discord: {discord})&message_type=success')
    
    return redirect(f'/admin?auth={auth}&message=Nie znaleziono {owner}&message_type=error')

@app.route('/admin/extend', methods=['POST'])
def admin_extend():
    """Przedłuża klienta"""
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return redirect(f'/admin?auth={auth}&message=Brak uprawnień&message_type=error')
    
    owner = request.form.get('owner')
    dni = int(request.form.get('dni', 7))
    
    klienci = wczytaj_klientow()
    
    if owner in klienci:
        stara_data = datetime.fromisoformat(klienci[owner]['wazny_do'])
        # Przedłuż od aktualnej daty ważności (nie od dziś)
        nowa_data = stara_data + timedelta(days=dni)
        klienci[owner]['wazny_do'] = nowa_data.isoformat()
        klienci[owner]['dni'] = klienci[owner].get('dni', 1) + dni
        zapisz_klientow(klienci)
        return redirect(f'/admin?auth={auth}&message=Przedłużono {owner} o {dni} dni&message_type=success')
    
    return redirect(f'/admin?auth={auth}&message=Nie znaleziono {owner}&message_type=error')

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """API dla statystyk"""
    auth = request.args.get('auth')
    if auth != HASLO_ADMINA:
        return jsonify({"error": "Brak dostępu"}), 403
    
    klienci = wczytaj_klientow()
    teraz = datetime.now()
    
    aktywni = 0
    wygasli = 0
    
    for dane in klienci.values():
        try:
            wazny_do = datetime.fromisoformat(dane['wazny_do'])
            if teraz <= wazny_do:
                aktywni += 1
            else:
                wygasli += 1
        except:
            wygasli += 1
    
    # Policz pliki
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
    """Strona główna - przekierowanie do panelu"""
    return redirect('/admin')

if __name__ == '__main__':
    # Przy starcie utwórz folder dane jeśli nie istnieje
    if not os.path.exists(FOLDER_Z_DANYMI):
        os.makedirs(FOLDER_Z_DANYMI)
        print(f"📁 Utworzono folder {FOLDER_Z_DANYMI}")
    
    # Utwórz plik klienci.json jeśli nie istnieje
    if not os.path.exists(PLIK_Z_KLIENTAMI):
        with open(PLIK_Z_KLIENTAMI, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        print(f"📁 Utworzono plik {PLIK_Z_KLIENTAMI}")
    
    print("=" * 50)
    print("🚀 FastFind API - Panel Admina uruchomiony!")
    print(f"🔑 Panel admina: http://127.0.0.1:5000/admin?auth={HASLO_ADMINA}")
    print(f"📁 Pliki w folderze: {FOLDER_Z_DANYMI}")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
