# Portable Developer Environment

ติดตั้งเครื่องมือ Developer ที่ใช้บ่อยบน **Windows 10/11 x64** จากหน้าจอเดียว โดยเน้นการติดตั้งแบบ **User / Portable** และตั้ง **User PATH แบบถาวร** ให้อัตโนมัติ จึงไม่ต้องเปิด PowerShell แบบ Administrator สำหรับการใช้งานปกติ

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

### CLI Productivity

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | PowerShell 7 (`pwsh`) | PowerShell รุ่นใหม่แบบ portable |
| Essential | jq | อ่าน ค้นหา และแปลง JSON จาก CLI |
| Essential | ripgrep (`rg`) | ค้นหาข้อความและ source code ความเร็วสูง |
| Recommended | fzf | Fuzzy finder แบบ interactive |

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
| Essential | SQLite CLI (`sqlite3`) | Embedded SQL database CLI |
| Recommended | DuckDB CLI | SQL analytics สำหรับ CSV / Parquet / JSON |
| Optional | XAMPP | Apache + PHP + MariaDB stack |

### Cloud / Platform

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | Google Cloud CLI | จัดการ Google Cloud |
| Recommended | cloudflared | Cloudflare Tunnel |
| Recommended | Supabase CLI | Supabase development / project CLI |

### DevOps / Infrastructure

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Recommended | Terraform | Infrastructure as Code |
| Recommended | kubectl | จัดการ Kubernetes cluster |
| Recommended | Helm | Package manager สำหรับ Kubernetes |
| Recommended | rclone | Copy / sync ไฟล์กับ Cloud และ Object Storage |

### Utilities

| ระดับ | โปรแกรม | ใช้ทำอะไร |
|---|---|---|
| Optional | Notepad++ | Lightweight editor |
| Optional | wget | Download จาก command line |

## Permanent User PATH เป็นข้อบังคับของ Installer

ทุกโปรแกรมใน Catalog ต้องประกาศตำแหน่ง PATH ของตัวเอง และหลังติดตั้งสำเร็จระบบจะตรวจว่าตำแหน่งนั้นมีอยู่จริงก่อนเพิ่มเข้า **User PATH แบบถาวร**

ถ้าโปรแกรมติดตั้งเสร็จแต่ตำแหน่ง PATH ที่กำหนดไม่ถูกสร้าง ระบบจะถือว่ารายการนั้น **FAILED** แทนการรายงานว่าสำเร็จแบบไม่สมบูรณ์

ระบบไม่แก้ `System PATH` โดยตรง และไม่ต้องใช้ Administrator สำหรับการติดตั้งปกติ

หลังติดตั้งให้เปิด PowerShell ใหม่หนึ่งครั้ง แล้วสามารถเรียกใช้ได้โดยตรง เช่น:

```powershell
git --version
gh --version
code --version
pwsh --version
jq --version
rg --version
fzf --version
node --version
npm --version
npx --version
pnpm --version
bun --version
codex --version
claude --version
uv --version
python --version
jupyter-lab --version
mysql --version
sqlite3 --version
duckdb --version
gcloud --version
cloudflared --version
supabase --version
terraform --version
kubectl version --client
helm version --short
rclone version
wget --version
```

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

## ใช้ผ่าน PowerShell

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
python .\installer.py --install jq ripgrep sqlite fzf duckdb powershell terraform kubectl helm rclone
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
├─ app.py                 # application flow / CLI / permanent PATH enforcement
├─ catalog.py             # รายชื่อโปรแกรม + dependencies + PATH contract
├─ config.py              # path/config กลาง
├─ models.py              # Program / Priority / Result
├─ ui.py                  # interactive terminal UI
├─ core/
│  ├─ archive.py          # ZIP/TAR + atomic replacement
│  ├─ environment.py      # permanent User PATH / environment
│  ├─ github.py           # GitHub release lookup
│  ├─ http.py             # download + retry
│  ├─ planner.py          # dependency resolution
│  └─ process.py          # subprocess + verification
└─ installers/
   ├─ foundation.py
   ├─ productivity.py
   ├─ javascript.py
   ├─ python_data.py
   ├─ data_tools.py
   ├─ database.py
   ├─ cloud.py
   ├─ devops.py
   └─ utilities.py
```

เวลาเพิ่มโปรแกรมใหม่ ต้องกำหนด `path_entries` ใน `Program(...)` ด้วย หากไม่กำหนด Installer จะไม่ยอมเริ่มทำงาน เพื่อป้องกันโปรแกรมถูกติดตั้งแต่เรียกใช้จาก Terminal ไม่ได้

## Validation

Pull Request มี GitHub Actions ตรวจอย่างน้อย:

```text
Python compile check
Dependency planner unit tests
Catalog uniqueness
Required tool registration
Permanent PATH contract for every program
PATH traversal / absolute-path rejection
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
- `kubectl` และ `Helm` ติดตั้ง CLI ได้โดยไม่ต้อง Admin แต่การใช้งานจริงต้องมี Kubernetes cluster/context ที่เข้าถึงได้

---

Repository: `firmeen/portable`
