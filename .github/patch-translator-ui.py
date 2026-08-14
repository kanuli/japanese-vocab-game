from pathlib import Path
import re

path = Path('translator.html')
text = path.read_text(encoding='utf-8')

# The Supertonic built-in voices are officially named F1-F5 / M1-M5.
# Show their official tonal descriptions so the selector is meaningful.
voice_select = '''<select id="voice">
<option value="F1">F1｜Calm・Steady｜沉穩冷靜女聲</option>
<option value="F2">F2｜Bright・Cheerful｜明亮活潑女聲</option>
<option value="F3" selected>F3｜Professional｜專業播音女聲</option>
<option value="F4">F4｜Crisp・Confident｜清晰自信女聲</option>
<option value="F5">F5｜Kind・Gentle｜溫柔親切女聲</option>
<option value="M1">M1｜Lively・Upbeat｜活力明快男聲</option>
<option value="M2">M2｜Deep・Calm｜低沉冷靜男聲</option>
<option value="M3">M3｜Authoritative｜成熟權威男聲</option>
<option value="M4">M4｜Soft・Friendly｜柔和親切男聲</option>
<option value="M5">M5｜Warm・Soothing｜溫暖舒緩男聲</option>
<option value="random">🎲 隨機｜Random style</option>
</select>'''

text, n = re.subn(r'<select id="voice">.*?</select>', voice_select, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Could not find Supertonic voice selector')

# The speed slider already provides slow playback, so remove the duplicate button.
text = text.replace('<button id="slow" class="btn">🐢 慢速日語</button>', '')

# Remove the obsolete slow-button event handler so the missing element cannot break JS setup.
text, n = re.subn(
    r";\$\('#slow'\)\.onclick=\(\)=>\{.*?\};\$\('#stop'\)",
    ";$('#stop')",
    text,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit('Could not find slow playback handler')

path.write_text(text, encoding='utf-8')
print('Translator UI patched: descriptive Supertonic styles + no redundant slow button')
