# Portable Developer Environment

ติดตั้งเครื่องมือ Developer ที่ใช้บ่อยบน **Windows 10/11 x64** จากหน้าจอเดียว โดยเน้นการติดตั้งแบบ **User / Portable** และตั้ง `PATH` ให้อัตโนมัติ จึงไม่ต้องเปิด PowerShell แบบ Administrator สำหรับการใช้งานปกติ

> ถ้าไม่ใช่โปรแกรมเมอร์: ดาวน์โหลด repo แล้ว **ดับเบิลคลิก `Install.cmd`** ได้เลย

## เริ่มใช้งานแบบง่ายที่สุด

1. ดาวน์โหลด repository นี้เป็น ZIP แล้วแตกไฟล์ หรือ Clone ด้วย Git
2. เปิดโฟลเดอร์ `portable`
3. ดับเบิลคลิก **`Install.cmd`**
4. ใช้ปุ่มลูกศรเลือกโปรแกรม
5. กด `Enter` หรือ `Space` เพื่อติ๊ก
6. เลื่อนไปที่ **INSTALL SELECTED** แล้วกด `Enter`
7. ตรวจรายการที่จะติดตั้ง แล้วกด `Enter` อีกครั้งเพื่อยืนยัน

`Install.cmd` จะพยายามใช้ Python ที่มีอยู่ก่อน หากเครื่องยังไม่มี Python จะเตรียม runtime ชั่วคราวไว้ใน `.bootstrap` ให้เองโดยไม่ต้องติดตั้งแบบ System-wide

## ปุ่มที่ใช้

| ปุ่ม | หน้าที่ |
|---|---|
| `↑` / `↓` | เลื่อนรายการ |
| `Enter` | เลือก/ยกเลิกโปรแกรม แล้วเลื่อนไปรายการถัดไป |
| `Space` | เลือก/ยกเลิก โดยไม่เลื่อน |
| `1` | เลือกเฉพาะ Essential |
| `2` | เลือก Essential + Recommended |
| `3` | เลือกทุกโปรแกรม |
| `C` | ล้างรายการที่เลือก |
| `I` | กระโดดไปปุ่ม Install |
| `Q` / `Esc` / `Ctrl+C` | ออกอย่างปลอดภัย |

เมนูใช้การวาดหน้าจอแบบ diff-based จึงไม่ล้าง PowerShell ทั้งหน้าจอทุกครั้งที่กดปุ่ม ลดอาการกระพริบจากเวอร์ชันเดิม

## โปรแกรมที่รองรับ

### Foundation

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Essential | Git | Version control |
| Recommended | GitHub CLI (`gh`) | ใช้งาน GitHub จาก Terminal |
| Essential | Visual Studio Code | Code editor |

### JavaScript / TypeScript

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Essential | Node.js LTS | Node + npm + npx |
| Recommended | pnpm | Package manager ที่เร็วและประหยัดพื้นที่ |
| Recommended | Bun | JavaScript runtime + toolkit |
| Optional | Yarn | Package manager / workspace compatibility |

### AI Developer CLI

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | Codex CLI | OpenAI coding agent |
| Recommended | Claude Code | Anthropic coding agent |

### Python / Data

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Essential | uv | Python package/runtime manager |
| Essential | Python Portable | Managed CPython ในโฟลเดอร์ portable |
| Recommended | JupyterLab | Notebook และ Data Analysis |
| Optional | pipx | Python CLI แยก environment |

### Database

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | MySQL | Database binaries |
| Recommended | DBeaver Community | Database GUI |
| Optional | XAMPP | Apache + PHP + MariaDB stack |

### Cloud / Platform

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | Google Cloud CLI | จัดการ Google Cloud |
| Recommended | cloudflared | Cloudflare Tunnel |
| Recommended | Supabase CLI | Supabase development / project CLI |

### Utilities

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Optional | Notepad++ | Lightweight editor |
| Optional | wget | Download จาก command line |

## Dependency จัดการให้อัตโนมัติ

ไม่จำเป็นต้องรู้ว่าโปรแกรมไหนต้องลงก่อน เช่น:

- เลือก `Codex CLI` → ระบบจะเตรียม `Node.js` ก่อนถ้ายังไม่มี
- เลือก `Claude Code` → ระบบจะเตรียม `Node.js` ก่อนถ้ายังไม่มี
- เลือก `Python Portable` → ระบบจะเตรียม `uv` ก่อน
- เลือก `JupyterLab` → ระบบจะเตรียม `uv` และ `Python Portable` ก่อน
- เลือก `GitHub CLI` → ระบบจะเตรียม `Git` ก่อน

ก่อนเริ่มติดตั้งจริง ระบบจะแสดง **Installation plan** ให้ตรวจอีกครั้ง

## โปรแกรมถูกเก็บไว้ที่ไหน

Source code กับโปรแกรมที่ดาวน์โหลดจะไม่ปนกัน:

```text
portable/
├─ Install.cmd                 # สำหรับผู้ใช้ทั่วไป
├─ installer.py               # Python entry point
├─ README.md
├─ portable_installer/        # source code ของ installer
├─ tests/                     # unit tests
├─ software/                  # โปรแกรมที่ติดตั้ง (สร้างอัตโนมัติ)
├─ logs/                      # log การติดตั้ง (สร้างอัตโนมัติ)
├─ .cache/                    # temporary downloads (สร้างอัตโนมัติ)
└─ .bootstrap/                # runtime ชั่วคราวเมื่อเครื่องไม่มี Python
```

`software/`, `logs/`, `.cache/` และ `.bootstrap/` จะไม่ถูก commit เข้า Git

## PATH แบบถาวร

Installer เพิ่มเฉพาะ path ที่จำเป็นเข้า **User PATH** ไม่แก้ `System PATH` โดยตรง ตัวอย่างหลังติดตั้ง:

```powershell
git --version
gh --version
node --version
npm --version
npx --version
pnpm --version
bun --version
code --version
mysql --version
uv --version
python --version
cloudflared --version
supabase --version
```

หลังติดตั้งเสร็จ แนะนำให้เปิด PowerShell หน้าต่างใหม่หนึ่งครั้งเพื่อให้ทุกโปรแกรมรับ PATH ล่าสุด

## ถ้าต้องการใช้ผ่าน PowerShell

เปิดเมนูปกติ:

```powershell
python .\installer.py
```

ดูโปรแกรมทั้งหมด:

```powershell
python .\installer.py --list
```

ดูแผนโดยยังไม่ติดตั้ง:

```powershell
python .\installer.py --preset recommended --dry-run
```

ติดตั้งโดยระบุชื่อ ID:

```powershell
python .\installer.py --install git gh vscode node pnpm
```

ติดตั้ง Recommended preset:

```powershell
python .\installer.py --preset recommended
```

สำหรับ automation ที่ไม่ต้องถามยืนยัน:

```powershell
python .\installer.py --install git gh --yes
```

## หากกด `Ctrl+C`

สามารถกด `Ctrl+C`, `Q` หรือ `Esc` เพื่อออกจากเมนูได้อย่างปลอดภัย Terminal จะคืน cursor และหน้าจอกลับสู่สภาพปกติ

ถ้ากด `Ctrl+C` ระหว่างดาวน์โหลด ไฟล์ `.part` ที่ดาวน์โหลดไม่ครบจะถูกลบทิ้ง และสามารถรันใหม่ได้

## Log และการแก้ปัญหา

Log อยู่ที่:

```text
logs\installer.log
```

ถ้ารายการใดติดตั้งไม่สำเร็จ รายการอื่นที่ไม่ขึ้นกับตัวนั้นยังสามารถดำเนินการต่อได้ ส่วนโปรแกรมที่ต้องพึ่ง dependency ที่ล้มเหลวจะถูกระบุเป็น `SKIPPED`

## สำหรับผู้พัฒนา / เพิ่มโปรแกรมใหม่

โค้ดถูกแยกตามหน้าที่:

```text
portable_installer/
├─ app.py                 # application flow / CLI
├─ catalog.py             # รายชื่อโปรแกรม + dependencies
├─ config.py              # path/config กลาง
├─ models.py              # Program / Priority / Result
├─ ui.py                  # interactive terminal UI
├─ core/
│  ├─ archive.py          # ZIP/TAR + atomic replacement
│  ├─ environment.py      # User PATH / environment
│  ├─ github.py           # GitHub release lookup
│  ├─ http.py             # download + retry
│  ├─ planner.py          # dependency resolution
│  └─ process.py          # subprocess + verification
└─ installers/
   ├─ foundation.py
   ├─ javascript.py
   ├─ python_data.py
   ├─ database.py
   ├─ cloud.py
   └─ utilities.py
```

เวลาเพิ่มโปรแกรมใหม่ โดยทั่วไปแก้เพียง installer ของ ecosystem นั้น และเพิ่ม `Program(...)` ใน `catalog.py` เท่านั้น ไม่ต้องแก้ UI หรือ dependency engine

## Validation

Pull Request จะมี GitHub Actions ตรวจอย่างน้อย:

```text
Python compile check
Unit tests for dependency planner
```

รันเองได้ด้วย:

```powershell
python -m compileall -q installer.py portable_installer tests
python -m unittest discover -s tests -v
```

## ข้อจำกัด

- รองรับ Windows x64
- ต้องใช้อินเทอร์เน็ตตอนดาวน์โหลดโปรแกรม
- บาง feature ของโปรแกรมปลายทางอาจต้องใช้สิทธิ์เพิ่มเอง เช่น การติดตั้ง service ของ `cloudflared` หรือ service/database บางประเภท
- Supabase CLI ใช้ได้โดยตรง แต่ local Supabase stack ยังต้องมี container runtime ที่รองรับ

---

Repository: `firmeen/portable`
