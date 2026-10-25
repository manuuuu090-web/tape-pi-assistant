#!/bin/bash
# Met a jour l'assistant depuis GitHub et relance l'app si du nouveau code est arrive.
# Lance par le minuteur (cron) et par le bouton "Mettre a jour" de l'ecran.
cd "$(dirname "$0")" || exit 1

BEFORE=$(git rev-parse HEAD 2>/dev/null)
git fetch origin main -q 2>/dev/null
git reset --hard origin/main -q 2>/dev/null
AFTER=$(git rev-parse HEAD 2>/dev/null)

if [ "$BEFORE" != "$AFTER" ]; then
    # installe d'eventuelles nouvelles dependances
    [ -f venv/bin/activate ] && source venv/bin/activate && pip install -q -r requirements.txt 2>/dev/null
    # relance le serveur (l'ecran se recharge tout seul en voyant la nouvelle version)
    pkill -f "python3 app.py" 2>/dev/null
    sleep 1
    source venv/bin/activate 2>/dev/null
    setsid nohup python3 app.py >/tmp/app.log 2>&1 &
fi
