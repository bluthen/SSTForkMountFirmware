import sqlite3
import requests
import json

conn = sqlite3.connect('../ssteq.sqlite', check_same_thread=False)

cur = conn.cursor()
cur.execute("SELECT postalcode, latitude, longitude, elevation from uscities order by postalcode")
zips = cur.fetchall()
for zip in zips:
    if not zip[3]:
        r = requests.get('http://localhost:8080/api/v1/lookup', params={'locations': str(zip[1])+','+str(zip[2])})
        if r.status_code == 200:
            v = r.json()
            print(json.dumps(v))
            cur2 = conn.cursor()
            print(zip[0])
            cur2.execute('UPDATE uscities set elevation = ? where postalcode = ?', (v['results'][0]['elevation'], zip[0]))
            conn.commit()
        else:
            raise Exception(r.text)

