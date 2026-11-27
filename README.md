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
| Essential | Windows Terminal (`wt`) | เปิด Terminal หลาย Tab/Pane, Fullscreen และเรียกใช้งานผ่าน CLI |
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
| Recommended | MySQL | Ready-to-use local database, port 3307 |
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

ทุกโปรแกรมใน Catalog รวม Windows Terminal ต้องมีไฟล์คำสั่งและ PATH contract ที่ตรวจสอบได้ ระบบบันทึก User PATH ผ่าน Registry หลังตรวจสอบไฟล์ พร้อมอัปเดต Process PATH สำหรับการติดตั้ง dependency

ซ่อม PATH ของทุกโปรแกรมที่ติดตั้งแล้วโดยไม่ดาวน์โหลดหรือติดตั้งซ้ำ:

~~~powershell
.\Install.cmd --repair-path
~~~

สำหรับ Windows Terminal ดู [คู่มือติดตั้งและใช้งาน wt](#windows-terminal-wt) ด้านล่าง

Portable PATH ถูกจัดให้อยู่ก่อน User PATH อื่น โดยไม่แก้ System PATH และไม่ลบ PATH อื่น หาก System PATH, Microsoft Store alias หรือเครื่องมือที่ใช้คำสั่งซ้ำกัน เช่น MySQL/XAMPP มี precedence สูงกว่า ระบบจะแจ้ง PATH CONFLICT เมื่อพบใน PATH; PowerShell aliases/functions ไม่ถูกแก้โดยอัตโนมัติ ใช้ `Get-Command wt -All` หรือ `where.exe wt` ตรวจสอบได้

ทุกโปรแกรมใน Catalog ต้องประกาศตำแหน่ง PATH ของตัวเอง และหลังติดตั้งสำเร็จระบบจะตรวจว่าตำแหน่งนั้นมีอยู่จริงก่อนเพิ่มเข้า **User PATH แบบถาวร**

ถ้าโปรแกรมติดตั้งเสร็จแต่ตำแหน่ง PATH ที่กำหนดไม่ถูกสร้าง ระบบจะถือว่ารายการนั้น **FAILED** แทนการรายงานว่าสำเร็จแบบไม่สมบูรณ์

ระบบไม่แก้ `System PATH` โดยตรง และไม่ต้องใช้ Administrator สำหรับการติดตั้งปกติ

หลังติดตั้งให้เปิด PowerShell ใหม่หนึ่งครั้ง แล้วสามารถเรียกใช้ได้โดยตรง เช่น:

```powershell
git --version
gh --version
code --version
where.exe wt
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

## Windows Terminal (`wt`)

Windows Terminal เป็นโปรแกรมสำหรับเปิด PowerShell, CMD และ shell อื่น ๆ ในหน้าต่างเดียว รองรับหลาย Tab, Split Pane, Fullscreen และการเปิดผ่านคำสั่ง `wt` จาก PowerShell/CMD

### 1. ติดตั้ง Windows Terminal

ดับเบิลคลิก `Install.cmd` แล้วเลือก **Windows Terminal** ในหมวด CLI Productivity หรือเปิด PowerShell ในโฟลเดอร์ portable แล้วรัน:

```powershell
.\Install.cmd --install wt --yes
```

หากต้องการติดตั้ง Windows Terminal พร้อม PowerShell 7:

```powershell
.\Install.cmd --install wt powershell --yes
```

Installer จะดาวน์โหลด Stable Windows x64 ZIP จาก [Microsoft](https://github.com/microsoft/terminal/releases/latest), แตกไฟล์, สร้าง `.portable` เพื่อเปิด Portable Mode และตั้ง Permanent User PATH ไปที่ `software/terminal` อัตโนมัติ โดยไม่ต้องใช้ Microsoft Store หรือ Administrator สำหรับการใช้งาน portable ตามปกติ

### 2. ตำแหน่งไฟล์และการเปิดโปรแกรม

```text
software/
└── terminal/
    ├── WindowsTerminal.exe
    ├── wt.exe หรือ wt.cmd
    ├── .portable
    ├── settings/          # สร้างเมื่อใช้งาน และเก็บไว้เมื่ออัปเดต
    └── ...
```

ดับเบิลคลิก `software/terminal/WindowsTerminal.exe` เพื่อเปิดโดยตรง หรือเปิด PowerShell/CMD **หน้าต่างใหม่** หลังติดตั้ง แล้วเรียกจากโฟลเดอร์ใดก็ได้:

```powershell
wt
```

หาก ZIP ไม่มี `wt.exe` Installer จะสร้าง `wt.cmd` เป็น launcher สำรองสำหรับส่ง arguments ไปยัง `WindowsTerminal.exe`

### 3. คำสั่ง wt ที่ใช้บ่อย

| คำสั่ง | หน้าที่ |
|---|---|
| `wt` | เปิด Windows Terminal |
| `wt -w new` | เปิดหน้าต่างใหม่ |
| `wt -F` | เปิดแบบ Fullscreen |
| `wt -M` | เปิดแบบ Maximized |
| `wt -d .` | เปิด Terminal ที่โฟลเดอร์ปัจจุบัน |
| `wt new-tab` | เปิดด้วยคำสั่ง new-tab |
| `wt split-pane` | เปิดด้วยคำสั่ง split-pane |
| `wt -p "Windows PowerShell"` | เปิดด้วยโปรไฟล์ Windows PowerShell (หากมีโปรไฟล์นี้) |

ตัวอย่างเปิดหน้าต่างใหม่แบบ Fullscreen ในโฟลเดอร์ปัจจุบัน:

```powershell
wt -w new -F -d .
```

### 4. ตรวจสอบและซ่อม Permanent PATH

เปิด PowerShell ใหม่ แล้วตรวจว่าคำสั่ง `wt` ชี้ไปที่ไฟล์ใด:

```powershell
Get-Command wt -All
where.exe wt
[Environment]::GetEnvironmentVariable("Path", "User") -split ';'
```

ตำแหน่งที่คาดหวังคือ `software/terminal/wt.exe` หรือ `software/terminal/wt.cmd` ภายใต้โฟลเดอร์โปรเจกต์

ถ้าพบว่า `wt` ยังไม่ถูก Recognized ให้กลับมาที่โฟลเดอร์ portable แล้วรัน:

```powershell
.\Install.cmd --repair-path
```

จากนั้นเปิด PowerShell/CMD ใหม่อีกครั้ง หาก Terminal host เดิมยังใช้ environment เก่า ให้ปิด host เดิมแล้วเปิดใหม่ ไม่ต้องติดตั้งโปรแกรมซ้ำเพียงเพื่อซ่อม PATH

หากมี Windows Terminal จาก Microsoft Store หรือ System PATH อยู่แล้ว ระบบอาจพบคำสั่งชื่อเดียวกัน ให้ตรวจผล `Get-Command wt -All` ก่อน และสามารถเปิด portable โดยตรงจากโฟลเดอร์โปรเจกต์ได้:

```powershell
& ".\software\terminal\WindowsTerminal.exe" -F
```

ไม่ต้องถอน Windows Terminal เดิมหรือแก้ System PATH; Portable Mode ไม่รองรับการตั้งเป็น Default Terminal ของ Windows ผ่านการตั้งค่าแบบ MSIX

## MySQL — Ready-to-Use Database Server

ติดตั้งผ่านเมนูโดยเลือก MySQL หรือรัน:

~~~powershell
.\Install.cmd --install mysql --yes
~~~

Installer ตรวจตำแหน่ง `software/mysql/bin` โดยอัตโนมัติจากตำแหน่งโปรเจกต์ ไม่ต้องค้นหาทุก Drive หรือรัน PowerShell Script เพิ่มเติม เมื่อมี binaries ครบแล้วจะใช้ตัวเดิมเพื่อป้องกันการอัปเกรด Server ทับฐานข้อมูลเดิมโดยไม่ตั้งใจ

สำหรับการติดตั้งใหม่ ระบบจะสร้าง:

- `software/mysql/data/` — โฟลเดอร์เก็บฐานข้อมูล พร้อม initialize ระบบ MySQL อัตโนมัติ
- `software/mysql/my.ini` — ตั้งค่า port 3307, bind-address 127.0.0.1, utf8mb4 และ utf8mb4_unicode_ci; ปิด MySQL X Protocol สำหรับการใช้งาน local นี้
- `software/mysql/start_mysql.bat` — ดับเบิลคลิกเพื่อเปิด MySQL Server
- Permanent User PATH และ Process PATH สำหรับ `mysql`, `mysqld`, `mysqldump` และ `mysqladmin` ผ่านระบบ PATH กลางของ Installer

### 1. เปิด MySQL Server

ดับเบิลคลิก `software/mysql/start_mysql.bat` หรือรัน:

~~~powershell
.\software\mysql\start_mysql.bat
~~~

Server จะทำงานในหน้าต่าง Console ไม่ติดตั้ง Windows Service และไม่เปิด Server ค้างไว้เองหลังติดตั้ง ตรวจว่า port 3307 ว่างก่อนเปิด

### 2. เชื่อมต่อ MySQL

เปิด PowerShell/CMD ใหม่เพื่อรับ PATH ล่าสุด:

~~~powershell
mysql -h 127.0.0.1 -P 3307 -u root
~~~

ค่าตั้งต้นสำหรับฐานข้อมูลที่เพิ่ง initialize:

| Setting | Value |
| --- | --- |
| Host | 127.0.0.1 |
| Port | 3307 |
| Username | root |
| Password | ว่าง (เฉพาะฐานข้อมูลใหม่) |
| Charset | utf8mb4 |
| Collation | utf8mb4_unicode_ci |

ใช้ค่าเดียวกันใน DBeaver (เลือก MySQL driver) ได้โดยตรง เมื่อเริ่มใช้งานควรตั้งรหัสผ่าน root ทันที เช่นผ่าน SQL:

~~~sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_UNIQUE_PASSWORD';
~~~

เปลี่ยนตัวอย่างรหัสผ่านก่อนรัน หลังตั้งรหัสผ่านให้เพิ่ม `-p` ในคำสั่ง mysql/mysqladmin เพื่อรับ password prompt ไม่ควรใช้ root รหัสผ่านว่างกับข้อมูลสำคัญหรือเปิดรับการเชื่อมต่อจากภายนอก

### 3. เริ่มสร้างฐานข้อมูล

~~~sql
SHOW DATABASES;
CREATE DATABASE my_database
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE my_database;
~~~

### 4. ปิด MySQL Server อย่างปลอดภัย

~~~powershell
mysqladmin -h 127.0.0.1 -P 3307 -u root shutdown
~~~

ถ้าตั้งรหัสผ่านแล้ว:

~~~powershell
mysqladmin -h 127.0.0.1 -P 3307 -u root -p shutdown
~~~

### 5. การติดตั้งซ้ำ / ฐานข้อมูลเดิม

- ไม่ initialize ซ้ำหากพบฐานข้อมูลที่ initialize แล้ว และไม่ลบ data, my.ini หรือ start_mysql.bat เดิม
- ถ้า data ไม่ว่างแต่ตรวจไม่พบ system database ที่สมบูรณ์ จะหยุดและแจ้งให้ตรวจสอบ/สำรองข้อมูลด้วยตนเอง
- my.ini ที่ปรับเองจะถูกเก็บไว้ ค่าการเชื่อมต่อเดิมอาจต่างจาก port 3307; หากยังไม่มีฐานข้อมูลและใช้ config ที่ต่างจากค่า generated ระบบจะไม่ initialize ทับโดยอัตโนมัติ
- ถ้าพบข้อมูล/config เดิมแต่ binaries ไม่ครบ ให้กู้ binaries เวอร์ชันที่เข้ากันได้ก่อน ไม่ดาวน์โหลด Server เวอร์ชันใหม่ทับข้อมูลเดิม
- การอัปเกรด MySQL ที่มีฐานข้อมูลจริงต้องสำรองข้อมูลและตรวจ upgrade path ตามเวอร์ชันเอง; Installer นี้จะใช้ binaries เดิมที่สมบูรณ์แทนการอัปเกรดอัตโนมัติ
- my.ini ใช้ absolute path; หากย้ายโปรเจกต์ ให้แก้ basedir/datadir ให้ตรงกับตำแหน่งใหม่ก่อนเปิด Server แล้วรัน `.\Install.cmd --repair-path`
- หากมี MySQL/XAMPP หลายตัว ให้ใช้ `Get-Command mysql -All` หรือ `where.exe mysql` ตรวจ PATH; เรียก `.\software\mysql\bin\mysql.exe` โดยตรงได้หากมี conflict
- หาก binaries เรียกไม่ได้ ให้ตรวจ Microsoft Visual C++ runtime ที่ MySQL เวอร์ชันนั้นต้องการ

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
python .\installer.py --install wt jq ripgrep sqlite fzf duckdb powershell terraform kubectl helm rclone
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
