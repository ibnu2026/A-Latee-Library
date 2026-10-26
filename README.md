# @ Latee Library - Desktop Application

**Version**: 1.0.0  
**Status**: ✅ Production Ready  
**Last Updated**: November 2025

---

## 📋 Quick Start

### Run from Source

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python LibraryDekstopApp.py
```

Generated databases, QR codes, reports, and build artifacts are local application data and are not stored in this repository.

---

## 🔑 Key Features

### 1. **Member Management**

- Register members with NIS, name, room, address
- Auto-generate unique QR codes + barcodes
- Fingerprint recognition (Deli ES151)
- Member card generation (PDF)

### 2. **Book Management**

- Generate and print QR labels for books; scan existing ISBN barcodes when needed
- Track inventory and borrowing status
- Search by code, title, author, publisher
- Export book list (Excel)

### 3. **Borrowing & Returns**

- Quick loan processing via QR scan
- Maximum of 2 active books per member; returned books free up a slot
- Members with unpaid fines cannot borrow until the fines are paid
- Automatic tracking with timestamps
- Late return penalties (configurable)
- Loan extension feature
- Return confirmation

### 4. **Visitor Tracking**

- Record visitor check-ins
- Fingerprint verification
- Visit duration tracking
- Export visitor reports (Excel)

### 5. **Reporting & Analytics**

- **Export Data**: Books, visitors, borrowing records
- **Monthly Statistics**: Visual charts (line + bar graphs)
- **PNG Charts**: High-quality visualization (150 DPI)
- **Excel Reports**: Comprehensive data export

### 6. **Staff Management**

- User authentication (username/password)
- Multiple librarian accounts (max 15)
- Password hashing (SHA256)
- Generate and save a librarian QR code without creating a librarian card

---

## 💻 System Requirements

### Hardware

- **OS**: Windows 10/11
- **RAM**: 4 GB minimum (8 GB recommended)
- **Disk**: 500 MB free space
- **Display**: 1280x720 minimum

### Optional Hardware

- **Barcode Scanner**: USB or RS232
- **QR Code Scanner**: USB camera
- **Fingerprint Reader**: Deli ES151
- **Fingerprint SDK**: Install the ZKTeco SDK separately to use the fingerprint reader

### Software

- **Python**: 3.10+ (if running from source)
- **Libraries**: See `requirements.txt`

---

## 📁 Database Structure

### Tables:

1. **books** - Book inventory
2. **members** - Member information + fingerprints
3. **borrows** - Borrowing transactions
4. **visitors** - Visitor check-ins
5. **users** - Librarian accounts

📍 **Location**:

- Windows: `%APPDATA%\Latee Library\library_data.db`
- Backup: `%USERPROFILE%\Documents\Latee Library\`

The application uses the database in the current Windows user's AppData folder. The NSIS installer only copies its starter database when this file does not already exist, so installing an update will not replace existing AppData data. Use the same Windows account that owns the existing database, and make a backup before installing an update.

---

## 🚀 Installation (NSIS)

1. Download installer: `setup.exe`
2. Run installer (choose Program Files location)
3. Creates `C:\Users\[username]\@ Latee Library\` for data storage
4. Desktop shortcut for quick access

**Note**: Executable path can be anywhere; data files always in user home directory for permission compatibility.

---

## 📊 Main Tabs

### 1. **Dashboard**

- Quick statistics overview
- Total books, members, active loans, visitors today
- Real-time status indicators

### 2. **Buku (Books)**

- Add/edit/delete books
- Search by multiple fields
- View book details and status

### 3. **Anggota (Members)**

- Member registration
- Generate QR codes
- View member details
- Manage fingerprints

### 4. **Peminjaman (Borrowing)**

- Scan member QR code
- Select book to borrow
- Auto-calculate return deadline
- Track loan status

### 5. **Pengembalian (Returns)**

- Quick return processing
- Fine calculation
- Loan extension
- View pending returns

### 6. **Pengunjung (Visitors)**

- Check-in with fingerprint or manual entry
- View visit history
- Export visitor data

### 7. **Laporan (Reports)**

- Export book inventory (Excel)
- Export visitor logs (Excel)
- Export borrowing records (Excel)
- Generate monthly statistics chart (PNG)

### 8. **Pengaturan (Settings)**

- User management
- Change password
- Logout

---

## 🔐 Authentication

### Default Admin Account

- **Username**: `admin`
- **Password**: `12345` (⚠️ Change on first login!)

### Creating New Users

1. Go to Settings tab
2. Click "Kelola Akun Pustakawan"
3. Enter username, password, full name
4. Maximum 12 accounts total

---

## 📤 Export Features

### Excel Reports

**Location**: `C:\Users\[username]\@ Latee Library\laporan\`

1. **Books** (`laporan_buku.xlsx`)
   - ID, Code, Category, Title, Author, Publisher, Barcode, Stock, Status, Borrowed Count

2. **Visitors** (`laporan_pengunjung.xlsx`)
   - ID, Name, Room, Fingerprint ID, Date, Time, Duration

3. **Borrowing** (`laporan_peminjaman.xlsx`)
   - ID, Book Title, Member Name, Room, Borrow Date, Due Date, Status, Return Date, Extended, Fine

### PNG Charts

1. **Monthly Statistics** (`grafik_statistik_YYYY.png`)
   - Line chart: Visitor vs Borrowing trends
   - Bar chart: Monthly comparison
   - Quality: 150 DPI

---

## ⚙️ Configuration

### Fine Settings (Edit in Code)

- **Late fine**: Adjustable per day
- **Fine start date**: Configurable grace period
- **Maximum fine**: Set per institution policy

### QR Code Settings

- **Size**: 16 pixels per module
- **Error Correction**: Level H (30% tolerance)
- **Logo**: Center white triangle background
- **Border**: 2 (quiet zone)

---

## 🐛 Troubleshooting

### Issue: "Access is denied" when generating QR

**Solution**: Ensure `C:\Users\[username]\@ Latee Library\` folder exists and is writable

### Issue: Export crashes / file not saved

**Solution**: Check folder permissions. Files save to user home directory, not Program Files

### Issue: Cannot scan fingerprint

**Solution**: Check USB connection to Deli ES151. Port should be COM3 (default) or adjust in code

### Issue: Barcode scanner not working

**Solution**: Scanner should emulate keyboard input. If not detected, use manual input option

---

## 📝 Common Tasks

### Add a New Book

1. Go to **Buku** tab
2. Click "Tambah Buku"
3. Fill: Code, Category, Title, Author, Publisher, Stock
4. Submit
5. (Optional) Generate QR code via button

### Register New Member

1. Go to **Anggota** tab
2. Click "Tambah Anggota"
3. Fill: NIS, Name, Room, Address
4. Submit
5. Click "Generate QR" button for barcode + card

### Record Loan

1. Go to **Peminjaman** tab
2. Click "Scan QR Member" or enter NIS
3. Select book from list
4. Click "Pinjamkan"
5. Auto-generates return deadline

### Record Return

1. Go to **Pengembalian** tab
2. Enter member NIS
3. View pending loans
4. Click "Terima Pengembalian"
5. Fine calculated automatically if late

### Export Statistics

1. Go to **Laporan** tab
2. Select:
   - "Export Data Buku" → Books list (Excel)
   - "Export Data Pengunjung" → Visitors (Excel)
   - "Export Data Peminjaman" → Borrowing (Excel)
   - "📊 Export Grafik Statistik" → Monthly chart (PNG)

---

## 🔧 Development

### Build Executable

```bash
python full_build.py
```

**Output**: `dist/@ Latee Library.exe` (113 MB)

### Build Installer (requires NSIS)

```bash
makensis setup.nsi
```

**Output**: `setup.exe` (~100 MB)

### Run Tests

```bash
pytest test_*.py
python test_export_grafik.py
```

### Dependencies

```bash
pip install -r requirements.txt
```

---

## 📚 Architecture

### Frontend

- **Framework**: PyQt5
- **Charts**: Matplotlib (Agg backend)
- **Packaging**: PyInstaller

### Backend

- **Database**: SQLite3
- **Authentication**: SHA256 hashing
- **File I/O**: openpyxl (Excel), PIL (Images)

### Scanning

- **QR Code**: qrcode library
- **Barcode**: pyzbar-x64 / fallback
- **Fingerprint**: Deli ES151 via serial

---

## 📞 Support

### Common Questions

**Q: Can I use this on Linux/Mac?**  
A: Possible with modifications. Core Python code is cross-platform; UI (PyQt5) is compatible. Fingerprint/barcode scanner support may vary.

**Q: How to backup database?**  
A: Copy `%APPDATA%\Latee Library\library_data.db` to external storage.

**Q: Can I migrate from Excel to this system?**  
A: Yes, programmatically import data via database functions. Contact developer for assistance.

**Q: What's the maximum number of records?**  
A: SQLite can handle 100k+ records easily. Performance optimal up to 1M records.

---

## 📄 License

© 2025 @ Latee Library. All rights reserved.

---

## 🎯 Roadmap

### Completed ✅

- QR code generation with logo
- Member + book management
- Borrowing/return tracking
- Visitor check-in
- Fine calculation
- Multi-user support
- Excel export
- Monthly statistics charts

### Planned 🔄

- Mobile app companion
- Cloud backup integration
- Advanced analytics
- Custom report builder
- Email notifications
- Barcode label printing

---

**For detailed feature guides, see separate documentation files.**
