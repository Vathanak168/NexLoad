with open('app.js', 'r', encoding='utf-8') as f:
    app = f.read()

app = app.replace('return \\`<div class="slide-item', 'return `<div class="slide-item')
app = app.replace('return \\`\n            <div class="slideshow', 'return `\n            <div class="slideshow')
app = app.replace('</div>\\`;', '</div>`;')
app = app.replace('</div>\\`', '</div>`')
app = app.replace('\\${', '${')

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app)
