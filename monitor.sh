while true; do
    if ! pgrep -f "main.py" > /dev/null; then
        cd /root/bot-cl && source venv/bin/activate && nohup python3 main.py > bot.log 2>&1 &
        echo "$(date): Бот перезапущен" >> monitor.log
    fi
    sleep 30
done
