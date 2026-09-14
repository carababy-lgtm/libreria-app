#!/bin/bash
# Avviato da Render prima di gunicorn
# Inizializza il DB e poi avvia il server
python -c "from database import init_db; init_db(); print('DB inizializzato.')"
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
