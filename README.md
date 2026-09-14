# Portable Software Installer

เครื่องมือสำหรับติดตั้งโปรแกรมที่ใช้บ่อยบน **Windows 64-bit** แบบรวมไว้ในโฟลเดอร์เดียว พร้อมตั้งค่า `PATH` ให้อัตโนมัติ

ไม่ต้องติดตั้งทีละโปรแกรม และไม่ต้องตั้ง PATH เอง

---

## โปรแกรมที่รองรับ

| โปรแกรม            | คำสั่งที่ใช้หลังติดตั้ง |
| ------------------ | ----------------------- |
| MySQL              | `mysql`                 |
| Notepad++          | `notepad++`             |
| OpenAI Codex CLI   | `codex`                 |
| Claude Code        | `claude`                |
| Visual Studio Code | `code`                  |
| Git                | `git`                   |
| GitHub CLI         | `gh`                    |
| DBeaver Community  | `dbeaver`               |
| XAMPP              | ใช้ `xampp-control.exe` |
| Node.js LTS        | `node`, `npm`, `npx`    |

---

# สิ่งที่ต้องมี

ก่อนเริ่มใช้งาน ต้องมี:

* Windows 10 หรือ Windows 11 แบบ 64-bit
* Python 3
* Internet
* สิทธิ์เขียนไฟล์ในโฟลเดอร์ที่เก็บโปรเจกต์

ตรวจสอบว่ามี Python แล้วหรือยัง:

```powershell
python --version
```

ถ้าแสดงประมาณนี้:

```text
Python 3.12.10
```

ถือว่าพร้อมใช้งาน

---

# วิธีติดตั้ง

## 1. ดาวน์โหลด Repository

ถ้ามี Git อยู่แล้ว:

```powershell
git clone https://github.com/firmeen/portable.git
cd portable
```

หรือดาวน์โหลด Repository เป็น ZIP จาก GitHub แล้วแตกไฟล์ก็ได้

โครงสร้างหลักจะมีเพียง:

```text
portable/
├── installer.py
└── README.md
```

---

## 2. เปิด PowerShell ในโฟลเดอร์

ตัวอย่าง:

```powershell
cd C:\Users\YOUR_NAME\project\portable
```

จากนั้นรัน:

```powershell
python .\installer.py
```

---

# วิธีเลือกโปรแกรม

เมื่อเปิด Installer จะเห็นหน้าตาประมาณนี้:

```text
PORTABLE SOFTWARE INSTALLER

[ ] MySQL
[ ] Notepad++
[ ] Codex CLI
[ ] Claude Code
[ ] Visual Studio Code
[ ] Git
[ ] GitHub CLI (gh)
[ ] DBeaver Community
[ ] XAMPP
[ ] Node.js LTS

[ INSTALL SELECTED ]
```

ใช้ปุ่ม:

```text
↑ / ↓       เลื่อนขึ้นหรือลง

Enter       เลือกโปรแกรม
Space       เลือก/ยกเลิกโปรแกรม

A           เลือกทั้งหมด
C           ยกเลิกทั้งหมด
Q           ออกจากโปรแกรม
```

สามารถเลือกหลายโปรแกรมพร้อมกันได้

ตัวอย่าง:

```text
[x] MySQL
[ ] Notepad++
[x] Codex CLI
[ ] Claude Code
[x] Visual Studio Code
[x] Git
[x] GitHub CLI (gh)
[ ] DBeaver Community
[ ] XAMPP
[x] Node.js LTS
```

จากนั้นเลื่อนลงไปที่:

```text
[ INSTALL SELECTED ]
```

แล้วกด:

```text
Enter
```

Installer จะจัดการส่วนที่เหลือให้อัตโนมัติ

---

# Installer ทำอะไรให้บ้าง

สำหรับโปรแกรมที่เลือก Installer จะทำงานประมาณนี้:

```text
ค้นหา Version ล่าสุด
        ↓
Download
        ↓
Extract / Install
        ↓
จัดเก็บในโฟลเดอร์ portable
        ↓
ตั้ง User PATH
        ↓
ตรวจสอบการติดตั้ง
        ↓
แสดงผลสำเร็จ / ล้มเหลว
```

ไม่ต้องเข้าไปเพิ่ม PATH ด้วยตัวเอง

---

# ตำแหน่งที่ติดตั้ง

โปรแกรมจะถูกเก็บอยู่ภายในโฟลเดอร์เดียวกับ `installer.py`

ตัวอย่าง:

```text
portable/
│
├── installer.py
├── README.md
│
├── mysql/
├── notepadpp/
├── codex/
├── claude/
├── VisualCode/
├── git/
├── github/
├── dbeaver/
├── xampp/
└── node/
```

ทำให้ง่ายต่อการ:

* Backup
* ย้ายเครื่อง
* ตรวจสอบไฟล์
* Update
* ลบโปรแกรม
* จัดการ PATH

---

# PATH คืออะไร

`PATH` ทำให้ Windows รู้ว่าจะหาโปรแกรมจากที่ไหน

เช่น ถ้าไม่มี PATH อาจต้องเรียก Git แบบนี้:

```powershell
C:\Users\YOUR_NAME\project\portable\git\cmd\git.exe --version
```

แต่เมื่อ Installer ตั้ง PATH ให้แล้ว สามารถใช้แค่:

```powershell
git --version
```

ได้ทันที

Installer จะเพิ่ม PATH ในระดับ:

```text
Current User
```

หรือ **User PATH**

จึงพยายามหลีกเลี่ยงการแก้ System PATH และโดยทั่วไปไม่จำเป็นต้อง Run as Administrator

---

# หลังติดตั้งเสร็จ

แนะนำให้ปิด PowerShell เดิม แล้วเปิด PowerShell ใหม่หนึ่งครั้ง

จากนั้นทดสอบโปรแกรมที่ติดตั้ง

## Git

```powershell
git --version
```

## GitHub CLI

```powershell
gh --version
```

## Node.js

```powershell
node --version
npm --version
npx --version
```

## OpenAI Codex

```powershell
codex --version
```

## Claude Code

```powershell
claude --version
```

## Visual Studio Code

```powershell
code --version
```

## MySQL

```powershell
mysql --version
```

---

# GitHub CLI

GitHub CLI ใช้คำสั่ง:

```powershell
gh
```

หลังติดตั้ง สามารถ Login GitHub ได้ด้วย:

```powershell
gh auth login
```

ตรวจสอบสถานะ:

```powershell
gh auth status
```

ตัวอย่างการ Clone Repository:

```powershell
gh repo clone firmeen/portable
```

---

# Git

หลังติดตั้งสามารถตั้งชื่อและ Email ได้

```powershell
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_EMAIL"
```

ตรวจสอบ:

```powershell
git config --global --list
```

---

# Node.js

การเลือก:

```text
Node.js LTS
```

จะติดตั้งเครื่องมือหลักมาด้วย:

```text
node
npm
npx
```

ทดสอบ:

```powershell
node --version
npm --version
npx --version
```

---

# Codex CLI

Codex ต้องใช้ Node.js / npm

แต่ไม่จำเป็นต้องเลือก Node.js เองก่อน

ถ้าเลือก:

```text
Codex CLI
```

แล้วเครื่องยังไม่มี Node.js ตัว Installer จะติดตั้ง Node.js ให้อัตโนมัติก่อน

หลังติดตั้ง:

```powershell
codex
```

หรือตรวจสอบเวอร์ชัน:

```powershell
codex --version
```

---

# Claude Code

Claude Code ใน Installer นี้ติดตั้งผ่าน npm เพื่อให้สามารถเก็บไว้ภายในโฟลเดอร์ Portable เดียวกันได้

ถ้ายังไม่มี Node.js Installer จะติดตั้ง Node.js ให้อัตโนมัติ

หลังติดตั้ง:

```powershell
claude
```

ตรวจสอบ:

```powershell
claude --version
```

---

# Visual Studio Code

Visual Studio Code จะติดตั้งแบบ ZIP/Portable

โฟลเดอร์หลัก:

```text
VisualCode/
```

และจะมี:

```text
VisualCode/data/
```

สำหรับ Portable Mode

หลังติดตั้งสามารถเปิด VS Code ด้วย:

```powershell
code .
```

ตัวอย่าง:

```powershell
cd C:\Users\YOUR_NAME\project\my-project
code .
```

---

# MySQL

MySQL จะถูกเก็บประมาณ:

```text
mysql/
├── bin/
├── lib/
└── ...
```

PATH ที่ถูกเพิ่มคือ:

```text
mysql\bin
```

ดังนั้นสามารถใช้:

```powershell
mysql --version
```

ได้จาก PowerShell

> การติดตั้ง MySQL Server และการสร้าง Database/User เป็นอีกขั้นตอนหนึ่ง Installer นี้เน้นดาวน์โหลด MySQL binaries และเตรียม PATH ให้พร้อมใช้งาน

---

# XAMPP

XAMPP จะอยู่ที่:

```text
xampp/
```

เปิด Control Panel ได้จาก:

```text
xampp\xampp-control.exe
```

XAMPP มีเครื่องมือหลายตัว เช่น:

```text
Apache
MariaDB / MySQL
PHP
phpMyAdmin
```

---

# DBeaver

DBeaver Community จะอยู่ที่:

```text
dbeaver/
```

ตัวโปรแกรมหลัก:

```text
dbeaver\dbeaver.exe
```

ใช้สำหรับจัดการ Database เช่น:

* MySQL
* MariaDB
* PostgreSQL
* SQLite
* SQL Server
* Oracle
* และ Database อื่น ๆ

---

# ติดตั้งใหม่หรือ Update

สามารถรัน:

```powershell
python .\installer.py
```

อีกครั้งได้

แล้วเลือกโปรแกรมที่ต้องการติดตั้งหรืออัปเดต

Installer จะค้นหา Release ล่าสุดสำหรับโปรแกรมที่รองรับการค้นหาเวอร์ชันล่าสุดอัตโนมัติ

---

# เลือกทุกโปรแกรม

เปิด:

```powershell
python .\installer.py
```

แล้วกด:

```text
A
```

จากนั้นเลือก:

```text
INSTALL SELECTED
```

และกด:

```text
Enter
```

---

# ถ้า Command ยังใช้ไม่ได้หลังติดตั้ง

เช่น:

```powershell
gh
```

แล้วขึ้นว่า:

```text
The term 'gh' is not recognized...
```

ให้ปิด PowerShell แล้วเปิดใหม่

จากนั้นลอง:

```powershell
gh --version
```

เพราะ PowerShell ที่เปิดอยู่ก่อนติดตั้งอาจยังใช้ PATH เก่าอยู่

---

# ตรวจสอบ PATH

ดู PATH ปัจจุบัน:

```powershell
$env:Path -split ";"
```

ดู User PATH ที่บันทึกไว้ถาวร:

```powershell
[Environment]::GetEnvironmentVariable("Path", "User") -split ";"
```

---

# ไม่จำเป็นต้อง Run as Administrator

Installer ออกแบบให้โปรแกรมส่วนใหญ่ติดตั้งภายในโฟลเดอร์ของผู้ใช้ และตั้งค่า:

```text
User PATH
```

แทน:

```text
System PATH
```

ดังนั้นโดยทั่วไปสามารถใช้ PowerShell ปกติได้

ไม่จำเป็นต้อง:

```text
Run as Administrator
```

เว้นแต่เครื่องหรือองค์กรมี Policy พิเศษ

---

# ต้องการย้ายโฟลเดอร์ Portable

แนะนำให้เลือกตำแหน่งหลักก่อนเริ่มติดตั้ง เช่น:

```text
C:\Users\YOUR_NAME\project\portable
```

หรือ:

```text
D:\Portable
```

แล้วอย่าย้ายหลังติดตั้ง เพราะ PATH จะอ้างอิงตำแหน่งเดิม

ถ้าต้องการย้ายจริง ให้รัน Installer ใหม่จากตำแหน่งใหม่เพื่อให้ PATH ถูกตั้งใหม่

---

# ตัวอย่างตำแหน่งที่แนะนำ

```text
D:\Portable
```

หรือ:

```text
C:\Users\YOUR_NAME\project\portable
```

ตัวอย่าง:

```powershell
cd D:\Portable
python .\installer.py
```

---

# Troubleshooting

## Python ไม่พบ

ถ้าขึ้น:

```text
python is not recognized
```

แสดงว่ายังไม่มี Python ใน PATH

ตรวจสอบด้วย:

```powershell
where.exe python
```

---

## Download ไม่สำเร็จ

ตรวจสอบ:

* Internet
* Firewall
* Proxy
* VPN
* SSL Certificate
* GitHub/API access

แล้วลองรันใหม่:

```powershell
python .\installer.py
```

---

## โปรแกรมหนึ่งติดตั้งล้มเหลว

ไม่จำเป็นต้องติดตั้งใหม่ทั้งหมด

เปิด Installer อีกครั้ง:

```powershell
python .\installer.py
```

แล้วเลือกเฉพาะโปรแกรมที่ล้มเหลว

---

# สรุปแบบสั้นที่สุด

Clone:

```powershell
git clone https://github.com/firmeen/portable.git
```

เข้าโฟลเดอร์:

```powershell
cd portable
```

เปิด Installer:

```powershell
python .\installer.py
```

เลือกโปรแกรม:

```text
↑ ↓       เลื่อน
Enter     เลือก
Space     เลือก/ยกเลิก
A         เลือกทั้งหมด
C         ล้างทั้งหมด
```

เลือก:

```text
INSTALL SELECTED
```

แล้วกด:

```text
Enter
```

เสร็จแล้วเปิด PowerShell ใหม่

จากนั้นใช้งานได้ เช่น:

```powershell
git --version
gh --version
node --version
npm --version
npx --version
code --version
mysql --version
codex --version
claude --version
```

---

## Repository

```text
https://github.com/firmeen/portable
```

โปรเจกต์นี้มีเป้าหมายเพื่อทำให้การเตรียม Development Environment บน Windows ง่ายที่สุด โดยรวมการดาวน์โหลด การติดตั้งแบบ Portable การตั้ง PATH และการตรวจสอบไว้ใน Installer ตัวเดียว
