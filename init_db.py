from app import app, seed_algorithm_settings
from models import db, Course, AlgorithmSettings

with app.app_context():
    db.create_all()
    print("Database recreated")


courses = [

    # First Year Courses
    ("BPH401","Physics", 1, "ITE"),
    ("BMA401","Mathematical Analysis I", 1, "ITE"),
    ("BAS401","Algebraic Structures", 1, "ITE"),
    ("BPG401","Programming I", 1, "ITE"),
    ("GEN301","English Language I", 1, "ITE"),
    ("GTW301","Communications Skills and Technical Writing", 1, "ITE"),
    ("BLA401","Linear Algebra", 1, "ITE"),
    ("BMA402","Mathematical Analysis II", 1, "ITE"),
    ("BEC401","Electronic Circuits", 1, "ITE"),
    ("BLC401","Logical Circuits", 1, "ITE"),
    ("BPG402","Programming II", 1, "ITE"),
    ("GEN401","English Language II", 1, "ITE"),

    # Second Year Courses
    ("BNA401","Numerical Analysis", 2, "ITE"),
    ("BWP401","Web Programming I", 2, "ITE"),
    ("BCA501","Computer Architecture I", 2, "ITE"),
    ("BSP501","Signal Processing", 2, "ITE"),
    ("BDA501","Data Structures and Algorithms I", 2, "ITE"),
    ("GEN501","English Language III", 2, "ITE"),
    ("GMN401","Fundamentals of Management", 2, "ITE"),
    ("BDM501","Discrete Mathematics", 2, "ITE"),
    ("BTS501","Telecommunication Systems", 2, "ITE"),
    ("BDB501","Database Systems I", 2, "ITE"),
    ("BDBL501","Database Systems Lab I", 2, "ITE"),
    ("BWP501","Web Programming II", 2, "ITE"),
    ("GEN502","English Language IV", 2, "ITE"),

    # Third Year Courses
    ("GAC501","Accounting", 3, "ITE"),
    ("BPS601","Probability & Statistics", 3, "ITE"),
    ("BOS501","Operating Systems I", 3, "ITE"),
    ("BOSL501","Operating Systems Lab I", 3, "ITE"),
    ("BAU501","Automata & Formal Languages", 3, "ITE"),
    ("BPG601","Programming III", 3, "ITE"),
    ("GEN601","English Language V", 3, "ITE"),
    ("BAI501","Artificial Intelligence", 3, "ITE"),
    ("BNT501","Computer Networks I", 3, "ITE"),
    ("BSE601","Software Engineering I", 3, "ITE"),
    ("BCM601","Compilers", 3, "ITE"),
    ("BCG601","Computer Graphics", 3, "ITE"),

    # Fourth Year Courses
    ("GPM601","IT Project Management", 4, "ITE"),
    ("BIA601","Intelligent Algorithms", 4, "ITE"),
    ("BMP601","Mobile Applications Programming", 4, "ITE"),
    ("BID601","Information Systems Analysis and Design", 4, "ITE"),
    ("BMM601","Multimedia Systems", 4, "ITE"),
    ("GET601","Ethics of Profession & Society", 4, "ITE"),
    ("MDA601","Big Data Analysis", 4, "ITE"),
    ("AIP601","Digital Image Processing", 4, "ITE"),
    ("ANN601","Neural Networks & Fuzzy Logic", 4, "ITE"),
    ("BPR601","Project I", 4, "ITE"),

    #Fifth Year Courses
    ("BIS601","Information System Security", 5, "ITE"),
    ("ACV601","Computer Vision", 5, "ITE"),
    ("ANL601","Natural Language Processing", 5, "ITE"),
    ("AML601","Machine Learning", 5, "ITE"),
    ("GEP601","Epistemology & Computer Science", 5, "ITE"),
    ("BSM601","Simulation, Modelling and Verification", 5, "ITE"),
    ("SIR601","Information Retrieval", 5, "ITE"),
    ("MBC601","Internet of Things and Block Chaining", 5, "ITE"),
    ("MDL601","Deep Learning", 5, "ITE"),
    ("BPR602","Project II", 5, "ITE"),

    

]




with app.app_context():
    for code, name, year, program in courses:
        existing = Course.query.filter_by(code=code).first()
        if not existing:
            db.session.add(
                Course(
                    code=code,
                    name=name,
                    academic_year=year,
                    program=program
                )
            )

    db.session.commit()
    print("Courses inserted successfully.")



with app.app_context():
    db.create_all()
    seed_algorithm_settings()

