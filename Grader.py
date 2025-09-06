import csv
import os
import random
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ---------- CONFIG ----------
USERS_FILE = "users.csv"
AUDIT_FILE = "audit.csv"
HEADERS = ["student_id", "name", "faculty", "level", "course", "unit", "grade", "mark", "semester"]

# ---------- FACULTY PASSCODES ----------
FACULTY_PASSCODES = {
    "Engineering": "ENG123",
    "Science": "SCI123",
    "Arts": "ART123",
    "Medicine": "MED123",
    "Law": "LAW123"
}

# ---------- GRADE SYSTEM ----------
GRADE_POINTS = {"A": 5.0, "B": 4.0, "C": 3.0, "D": 2.0, "E": 1.0, "F": 0.0}
GRADE_RANGES = {"A": (70, 100), "B": (60, 69), "C": (50, 59), "D": (45, 49), "E": (40, 44), "F": (0, 39)}

# ---------- HELPERS ----------
def ensure_csv_exists(file, headers):
    """Ensure CSV file exists with headers."""
    if not os.path.exists(file):
        with open(file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()

def hash_password(password):
    """Return SHA256 hash of the password."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def grade_to_points(grade): return GRADE_POINTS.get(grade.upper(), 0.0)
def generate_random_mark(grade): return random.randint(*GRADE_RANGES.get(grade.upper(), (0, 100)))
def class_of_degree(gpa):
    if gpa >= 4.50: return "First Class"
    elif gpa >= 3.50: return "Second Class Upper (2:1)"
    elif gpa >= 2.40: return "Second Class Lower (2:2)"
    elif gpa >= 1.50: return "Third Class"
    return "Fail"
def safe_unit(v): 
    try: return int(float(v))
    except: return 0

def get_level_from_id(sid):
    for lvl in ["100","200","300","400","500"]:
        if lvl in sid: return lvl
    return "general"
def get_grades_file(level): return f"grades_{level}.csv"

def validate_grade(grade):
    """Validate grade input."""
    return grade.upper() in GRADE_POINTS

def log_action(action, user_id, details):
    """Log actions to audit.csv."""
    ensure_csv_exists(AUDIT_FILE, ["timestamp", "action", "user_id", "details"])
    with open(AUDIT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), action, user_id, details])

def read_csv(file, headers):
    ensure_csv_exists(file, headers)
    with open(file, "r", newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def write_csv(file, rows, headers):
    with open(file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers); w.writeheader(); w.writerows(rows)
def read_all_levels(sid):
    res = []
    for lvl in ["100","200","300","400","500","general"]:
        f = get_grades_file(lvl)
        ensure_csv_exists(f, HEADERS)
        for r in read_csv(f,HEADERS):
            if r["student_id"] == sid: res.append(r)
    return res

# ---------- USER MGMT ----------
def signup():
    """Register a new staff or student."""
    role = input("Signup as (staff/student): ").strip().lower()
    users = read_csv(USERS_FILE, ["role","id","password","extra1","extra2"])
    if role=="staff":
        sid = input("Staff Username: ").strip()
        pwd = hash_password(input("Password: ").strip())
        course = input("Course Code: ").strip()
        fac = input("Faculty: ").strip()
        passcode = input(f"Faculty Passcode for {fac}: ").strip()
        if FACULTY_PASSCODES.get(fac)!=passcode:
            print("[!] Invalid passcode"); return
        users.append({"role":"staff","id":sid,"password":pwd,"extra1":course,"extra2":fac})
        log_action("signup_staff", sid, f"{fac} - {course}")
    elif role=="student":
        sid = input("Student ID: ").strip()
        pwd = hash_password(input("Password: ").strip())
        fac = input("Faculty: ").strip()
        name = input("Your Full Name: ").strip()
        passcode = input(f"Faculty Passcode for {fac}: ").strip()
        if FACULTY_PASSCODES.get(fac)!=passcode:
            print("[!] Invalid passcode"); return
        users.append({"role":"student","id":sid,"password":pwd,"extra1":fac,"extra2":name})
        log_action("signup_student", sid, name)
    else:
        print("[!] Invalid role"); return
    write_csv(USERS_FILE, users, ["role","id","password","extra1","extra2"])
    print("[OK] Registered.")

def login(role):
    """Authenticate a user by role."""
    users = read_csv(USERS_FILE, ["role","id","password","extra1","extra2"])
    uid = input(f"{role.capitalize()} ID: ").strip()
    pwd = hash_password(input("Password: ").strip())
    for u in users:
        if u["role"]==role and u["id"]==uid and u["password"]==pwd:
            print("[OK] Login")
            log_action("login", uid, role)
            return u
    print("[!] Login failed")
    log_action("login_failed", uid, role)
    return None

# ---------- STUDENT RESULTS ----------
def view_student_results(sid):
    """Show results for a student."""
    rows = read_all_levels(sid)
    if not rows:
        print("[!] No grades")
        return
    student_name = rows[0]["name"] if "name" in rows[0] else ""
    print(f"\n--- Results for {student_name} ({sid}) ---")
    print("Course | Unit | Grade | Mark | Semester"); print("----------------------------------------")
    pts,units=0,0
    for r in rows:
        print(f"{r['course']} | {r['unit']} | {r['grade']} | {r['mark']} | {r['semester']}")
        u = safe_unit(r["unit"])
        pts += grade_to_points(r["grade"])*u
        units += u
    gpa = pts/units if units else 0
    print(f"GPA: {gpa:.2f}  Class: {class_of_degree(gpa)}")
    log_action("view_student_results", sid, f"GPA:{gpa:.2f}")

# ---------- STAFF GRADING ----------
def add_bulk_grades(staff):
    """Add grades for all students in a faculty-level-course."""
    fac = staff["extra2"]
    lvl = input("Enter Level: ").strip()
    course = staff["extra1"]
    unit = input("Course Unit: ").strip()
    sem = input("Semester: ").strip()
    users = read_csv(USERS_FILE, ["role","id","password","extra1","extra2"])
    studs = [u for u in users if u["role"]=="student" and u["extra1"]==fac and get_level_from_id(u["id"])==lvl]
    if not studs: print("[!] No students"); return
    file = get_grades_file(lvl)
    rows = read_csv(file, HEADERS)
    for s in studs:
        while True:
            g = input(f"Grade for {s['extra2']} ({s['id']}): ").upper().strip()
            if validate_grade(g): break
            print("[!] Invalid grade. Must be A-F.")
        mark = generate_random_mark(g)
        ch = input(f"Auto mark {mark}, override? ")
        if ch.isdigit():
            m = int(ch)
            lo,hi = GRADE_RANGES[g]
            mark = m if lo<=m<=hi else mark
        rows.append({"student_id":s["id"],"name":s["extra2"],"faculty":fac,"level":lvl,"course":course,"unit":unit,"grade":g,"mark":mark,"semester":sem})
        log_action("add_grade", staff["id"], f"{s['id']} {g} {mark}")
    write_csv(file, rows, HEADERS)
    print("[OK] Grades saved.")

# ---------- RANKINGS ----------
def get_rankings(fac, lvl=None):
    """Return sorted rankings for a faculty (and optionally level)."""
    studs = {}
    lvls = [lvl] if lvl else ["100","200","300","400","500","general"]
    for l in lvls:
        f = get_grades_file(l)
        ensure_csv_exists(f, HEADERS)
        for r in read_csv(f,HEADERS):
            if r["faculty"]!=fac: continue
            studs.setdefault(r["student_id"],[]).append(r)
    res = []
    for s,recs in studs.items():
        pts = sum(grade_to_points(r["grade"])*safe_unit(r["unit"]) for r in recs)
        units = sum(safe_unit(r["unit"]) for r in recs)
        gpa = pts/units if units else 0
        res.append((s, gpa, class_of_degree(gpa), recs[0]["name"] if "name" in recs[0] else ""))
    return sorted(res, key=lambda x:x[1], reverse=True)

def print_rankings(fac, lvl=None):
    """Print rankings for faculty (and optionally level)."""
    ranks = get_rankings(fac, lvl)
    if not ranks: print("[!] No ranking data."); return
    title = f"{fac} Faculty {'Level '+lvl if lvl else 'Cumulative'} Rankings"
    print("\n"+title+"\n"+"="*len(title))
    print(f"{'Rank':<6}{'Student ID':<15}{'Name':<20}{'GPA':<8}{'Class'}")
    for i, (s, g, c, n) in enumerate(ranks, start=1):
        print(f"{i:<6}{s:<15}{n:<20}{g:.2f}   {c}")
    log_action("print_rankings", fac, f"level:{lvl}")

def export_rankings_pdf(fac, lvl=None):
    """Export rankings as PDF."""
    ranks = get_rankings(fac, lvl)
    if not ranks: print("[!] No data"); return
    title = f"{fac} Faculty {'Level '+lvl if lvl else 'Cumulative'} Rankings"
    fn = f"Ranking_{fac}_{lvl if lvl else 'All'}.pdf"
    doc = SimpleDocTemplate(fn, pagesize=A4); el = []; st = getSampleStyleSheet()
    el+=[Paragraph(title, st["Title"]), Spacer(1,12)]
    data = [["Rank","Student ID","Name","GPA","Class"]] + [[i+1,s,n,f"{g:.2f}",c] for i,(s,g,c,n) in enumerate(ranks)]
    t = Table(data); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black),("BACKGROUND",(0,0),(-1,0),colors.gray)]))
    el.append(t); doc.build(el); print(f"[OK] Rankings PDF: {fn}")
    log_action("export_rankings_pdf", fac, f"{fn}")

# ---------- TRANSCRIPT ----------
def generate_transcript(sid):
    """Generate and display transcript for a student."""
    rows = read_all_levels(sid)
    if not rows: print("[!] No grades"); return
    fac = rows[0]["faculty"]; lvl = rows[0]["level"]
    name = rows[0]["name"] if "name" in rows[0] else ""
    pts,units=0,0
    for r in rows:
        u = safe_unit(r["unit"])
        pts += grade_to_points(r["grade"])*u
        units += u
    gpa = pts/units if units else 0
    deg = class_of_degree(gpa)

    # Rank
    lvl_ranks = get_rankings(fac, lvl)
    cum_ranks = get_rankings(fac)
    lvl_rank = next((i+1 for i,(s,g,c,n) in enumerate(lvl_ranks) if s==sid), None)
    cum_rank = next((i+1 for i,(s,g,c,n) in enumerate(cum_ranks) if s==sid), None)

    # Console
    print("\n--- University of Ilorin ---")
    print(f"Name: {name}\nStudent ID: {sid}\nFaculty: {fac}\nLevel: {lvl}")
    print("Course | Unit | Grade | Mark | Semester")
    for r in rows: print(f"{r['course']} | {r['unit']} | {r['grade']} | {r['mark']} | {r['semester']}")
    print(f"GPA: {gpa:.2f} ({deg})")
    if lvl_rank: print(f"Level Rank: #{lvl_rank} of {len(lvl_ranks)}")
    if cum_rank: print(f"Cumulative Rank: #{cum_rank} of {len(cum_ranks)}")

    # PDF
    fn = f"Transcript_{sid}.pdf"
    doc = SimpleDocTemplate(fn, pagesize=A4)
    el = []; st = getSampleStyleSheet()
    el+=[Paragraph("University of Ilorin (Transcript)",st["Title"]),Spacer(1,12),
         Paragraph(f"Name: {name}",st["Normal"]),
         Paragraph(f"Student ID: {sid}",st["Normal"]),
         Paragraph(f"Faculty: {fac}",st["Normal"]),
         Paragraph(f"Level: {lvl}",st["Normal"]),Spacer(1,12)]
    data = [["Course","Unit","Grade","Mark","Semester"]] + [[r["course"],r["unit"],r["grade"],r["mark"],r["semester"]] for r in rows]
    t = Table(data); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black),("BACKGROUND",(0,0),(-1,0),colors.gray)]))
    el += [t, Spacer(1,12), Paragraph(f"GPA: {gpa:.2f} ({deg})",st["Normal"])]
    if lvl_rank: el.append(Paragraph(f"Level Rank: #{lvl_rank} of {len(lvl_ranks)}",st["Normal"]))
    if cum_rank: el.append(Paragraph(f"Cumulative Rank: #{cum_rank} of {len(cum_ranks)}",st["Normal"]))
    doc.build(el); print(f"[OK] Transcript PDF created: {fn}")
    log_action("generate_transcript", sid, fn)

# ---------- DASHBOARDS ----------
def staff_dashboard(staff):
    """Menu for staff actions."""
    while True:
        print(f"\n[STAFF MENU - {staff['extra2']} Faculty]")
        print("1=Add Grades\n2=View Student Results\n3=View Level Rankings\n4=View Cumulative Rankings\n5=Export Level Rankings (PDF)\n6=Export Cumulative Rankings (PDF)\n7=Logout")
        c = input("Choice: ").strip()
        if c == "1": add_bulk_grades(staff)
        elif c == "2": view_student_results(input("Student ID: ").strip())
        elif c == "3": print_rankings(staff["extra2"],input("Enter Level: ").strip())
        elif c == "4": print_rankings(staff["extra2"])
        elif c == "5": export_rankings_pdf(staff["extra2"],input("Enter Level: ").strip())
        elif c == "6": export_rankings_pdf(staff["extra2"])
        elif c == "7": break
        else: print("[!] Invalid choice.")

def student_dashboard(stu):
    """Menu for student actions."""
    while True:
        print(f"\n[STUDENT MENU - {stu['extra1']} Faculty]")
        print("1=Results\n2=Transcript\n3=Logout")
        c = input("Choice: ").strip()
        if c == "1": view_student_results(stu["id"])
        elif c == "2": generate_transcript(stu["id"])
        elif c == "3": break
        else: print("[!] Invalid choice.")

# ---------- MAIN ----------
def main():
    """Main menu loop."""
    while True:
        print("\n[MAIN] 1=Signup 2=Login Staff 3=Login Student 4=Exit")
        c = input("Choice: ").strip()
        if c == "1": signup()
        elif c == "2":
            s = login("staff")
            if s: staff_dashboard(s)
        elif c == "3":
            st = login("student")
            if st: student_dashboard(st)
        elif c == "4":
            print("Exiting...")
            break
        else:
            print("[!] Invalid choice.")

if __name__=="__main__": main()
