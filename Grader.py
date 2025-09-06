import csv
import os
import random
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ---------- CONFIG ----------
USERS_FILE = "users.csv"
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

def read_csv(file, headers):
    if not os.path.exists(file): return []
    with open(file, "r", newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def write_csv(file, rows, headers):
    with open(file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers); w.writeheader(); w.writerows(rows)
def read_all_levels(sid):
    res = []
    for lvl in ["100","200","300","400","500","general"]:
        f = get_grades_file(lvl)
        if os.path.exists(f):
            for r in read_csv(f,HEADERS):
                if r["student_id"] == sid: res.append(r)
    return res

# ---------- USER MGMT ----------
def signup():
    role = input("Signup as (staff/student): ").lower()
    users = read_csv(USERS_FILE, ["role","id","password","extra1","extra2"])
    if role=="staff":
        sid = input("Staff Username: "); pwd = input("Password: "); course=input("Course Code: "); fac=input("Faculty: ")
        if FACULTY_PASSCODES.get(fac)!=input(f"Faculty Passcode for {fac}: "): print("[!] Invalid passcode"); return
        users.append({"role":"staff","id":sid,"password":pwd,"extra1":course,"extra2":fac})
    elif role=="student":
        name:{name}
        sid = input("Student ID: "); pwd=input("Password: "); fac=input("Faculty: "); name=input("Your Full Name: ")
        if FACULTY_PASSCODES.get(fac)!=input(f"Faculty Passcode for {fac}: "): print("[!] Invalid passcode"); return
        users.append({"role":"student","id":sid,"password":pwd,"extra1":fac,"extra2":name})
    else: print("[!] Invalid role"); return
    write_csv(USERS_FILE,users,["role","id","password","extra1","extra2"]); print("[OK] Registered.")

def login(role):
    users=read_csv(USERS_FILE,["role","id","password","extra1","extra2"])
    uid=input(f"{role.capitalize()} ID: "); pwd=input("Password: ")
    for u in users:
        if u["role"]==role and u["id"]==uid and u["password"]==pwd: print("[OK] Login"); return u
    print("[!] Login failed"); return None

# ---------- STUDENT RESULTS ----------
def view_student_results(sid):
    rows=read_all_levels(sid)
    if not rows: print("[!] No grades"); return
    name : {name}
    print(f"\n{name}")
    print(f"\n--- Results for {sid},---")
    print("Course | Unit | Grade | Mark | Semester"); print("----------------------------------------")
    pts,units=0,0
    for r in rows:
        print(f"{r['course']} | {r['unit']} | {r['grade']} | {r['mark']} | {r['semester']}")
        u=safe_unit(r["unit"]); pts+=grade_to_points(r["grade"])*u; units+=u
    gpa=pts/units if units else 0; print(f"GPA: {gpa:.2f}  Class: {class_of_degree(gpa)}")

# ---------- STAFF GRADING ----------
def add_bulk_grades(staff):
    fac=staff["extra2"]; lvl=input("Enter Level: "); course=staff["extra1"]; unit=input("Course Unit: "); sem=input("Semester: ")
    users=read_csv(USERS_FILE,["role","id","password","extra1","extra2"])
    studs=[u for u in users if u["role"]=="student" and u["extra1"]==fac and get_level_from_id(u["id"])==lvl]
    if not studs: print("[!] No students"); return
    file=get_grades_file(lvl); rows=read_csv(file,HEADERS)
    for s in studs:
        g=input(f"Grade for {s['id']}: ").upper(); mark=generate_random_mark(g); ch=input(f"Auto mark {mark}, override? ")
        if ch.isdigit(): m=int(ch); lo,hi=GRADE_RANGES[g]; mark=m if lo<=m<=hi else mark
        rows.append({"student_id":s["id"],"name":s["id"],"faculty":fac,"level":lvl,"course":course,"unit":unit,"grade":g,"mark":mark,"semester":sem})
    write_csv(file,rows,HEADERS); print("[OK] Grades saved.")

# ---------- RANKINGS ----------
def get_rankings(fac,lvl=None):
    studs={}
    lvls=[lvl] if lvl else ["100","200","300","400","500","general"]
    for l in lvls:
        f=get_grades_file(l)
        if os.path.exists(f):
            for r in read_csv(f,HEADERS):
                if r["faculty"]!=fac: continue
                studs.setdefault(r["student_id"],[]).append(r)
    res=[]
    for s,recs in studs.items():
        pts=sum(grade_to_points(r["grade"])*safe_unit(r["unit"]) for r in recs)
        units=sum(safe_unit(r["unit"]) for r in recs)
        gpa=pts/units if units else 0
        res.append((s,gpa,class_of_degree(gpa)))
    return sorted(res,key=lambda x:x[1],reverse=True)

def print_rankings(fac, lvl=None):
    ranks=get_rankings(fac,lvl)
    if not ranks: print("[!] No ranking data."); return
    title=f"{fac} Faculty {'Level '+lvl if lvl else 'Cumulative'} Rankings"
    print("\n"+title+"\n"+"="*len(title))
    print(f"{'Rank':<6}{'Student ID':<15}{'GPA':<8}{'Class'}")
    for i,(s,g,c) in enumerate(ranks,start=1):
        print(f"{i:<6}{s:<15}{g:.2f}   {c}")

def export_rankings_pdf(fac,lvl=None):
    ranks=get_rankings(fac,lvl)
    if not ranks: print("[!] No data"); return
    title=f"{fac} Faculty {'Level '+lvl if lvl else 'Cumulative'} Rankings"
    fn=f"Ranking_{fac}_{lvl if lvl else 'All'}.pdf"
    doc=SimpleDocTemplate(fn,pagesize=A4); el=[]; st=getSampleStyleSheet()
    el+=[Paragraph(title,st["Title"]),Spacer(1,12)]
    data=[["Rank","Student ID","GPA","Class"]]+[[i+1,s,f"{g:.2f}",c] for i,(s,g,c) in enumerate(ranks)]
    t=Table(data); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black),("BACKGROUND",(0,0),(-1,0),colors.gray)]))
    el.append(t); doc.build(el); print(f"[OK] Rankings PDF: {fn}")

# ---------- TRANSCRIPT ----------
def generate_transcript(sid):
    rows=read_all_levels(sid)
    if not rows: print("[!] No grades"); return
    fac=rows[0]["faculty"]; lvl=rows[0]["level"]
    pts,units=0,0
    for r in rows: u=safe_unit(r["unit"]); pts+=grade_to_points(r["grade"])*u; units+=u
    gpa=pts/units if units else 0; deg=class_of_degree(gpa)

    # Rank
    lvl_ranks=get_rankings(fac,lvl); cum_ranks=get_rankings(fac)
    lvl_rank=next((i+1 for i,(s,g,c) in enumerate(lvl_ranks) if s==sid),None)
    cum_rank=next((i+1 for i,(s,g,c) in enumerate(cum_ranks) if s==sid),None)

    # Console
    print("\n--- University of Ilorin. ---")
    print(f"Student ID: {sid}\nFaculty: {fac}\nLevel: {lvl}")
    print("Course | Unit | Grade | Mark | Semester")
    for r in rows: print(f"{r['course']} | {r['unit']} | {r['grade']} | {r['mark']} | {r['semester']}")
    print(f"GPA: {gpa:.2f} ({deg})")
    if lvl_rank: print(f"Level Rank: #{lvl_rank} of {len(lvl_ranks)}")
    if cum_rank: print(f"Cumulative Rank: #{cum_rank} of {len(cum_ranks)}")

    # PDF
    fn=f"Transcript_{sid}.pdf"; doc=SimpleDocTemplate(fn,pagesize=A4); el=[]; st=getSampleStyleSheet()
    el+=[Paragraph("University of ILorin(Transcript)",st["Title"]),Spacer(1,12),Paragraph(f"Student ID: {sid}",st["Normal"]),
         Paragraph(f"Faculty: {fac}",st["Normal"]),Paragraph(f"Level: {lvl}",st["Normal"]),Spacer(1,12)]
    data=[["Course","Unit","Grade","Mark","Semester"]]+[[r["course"],r["unit"],r["grade"],r["mark"],r["semester"]] for r in rows]
    t=Table(data); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black),("BACKGROUND",(0,0),(-1,0),colors.gray)]))
    el+=[t,Spacer(1,12),Paragraph(f"GPA: {gpa:.2f} ({deg})",st["Normal"])]
    if lvl_rank: el.append(Paragraph(f"Level Rank: #{lvl_rank} of {len(lvl_ranks)}",st["Normal"]))
    if cum_rank: el.append(Paragraph(f"Cumulative Rank: #{cum_rank} of {len(cum_ranks)}",st["Normal"]))
    doc.build(el); print(f"[OK] Transcript PDF created: {fn}")

# ---------- DASHBOARDS ----------
def staff_dashboard(staff):
    while True:
        print(f"\n[STAFF MENU - {staff['extra2']} Faculty]")
        print("1=Add Grades 2=View Student Results 3=View Level Rankings 4=View Cumulative Rankings 5=Export Level Rankings (PDF) 6=Export Cumulative Rankings (PDF) 7=Logout")
        c=input("Choice: ")
        if c=="1": add_bulk_grades(staff)
        elif c=="2": view_student_results(input("Student ID: "))
        elif c=="3": print_rankings(staff["extra2"],input("Enter Level: "))
        elif c=="4": print_rankings(staff["extra2"])
        elif c=="5": export_rankings_pdf(staff["extra2"],input("Enter Level: "))
        elif c=="6": export_rankings_pdf(staff["extra2"])
        elif c=="7": break

def student_dashboard(stu):
    while True:
        print(f"\n[STUDENT MENU - {stu['extra1']} Faculty]")
        print("1=Results 2=Transcript 3=Logout")
        c=input("Choice: ")
        if c=="1": view_student_results(stu["id"])
        elif c=="2": generate_transcript(stu["id"])
        elif c=="3": break

# ---------- MAIN ----------
def main():
    while True:
        print("\n[MAIN] 1=Signup 2=Login Staff 3=Login Student 4=Exit")
        c=input("Choice: ")
        if c=="1": signup()
        elif c=="2": s=login("staff"); 
        if c=="2" and s: staff_dashboard(s)
        elif c=="3": st=login("student"); 
        if c=="3" and st: student_dashboard(st)
        elif c=="4":
            print("Exiting...")
            print(copyright&"Smart Core") 
            break

if __name__=="__main__": main()
