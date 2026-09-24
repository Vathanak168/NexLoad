with open('app.js', 'r', encoding='utf-8') as f:
    app = f.read()

app = app.replace('\\`', '`')

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app)
