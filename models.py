from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()




class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")
    is_banned = db.Column(db.Boolean, default=False)

    # Password reset fields
    reset_token = db.Column(db.String(255), nullable=True, unique=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    preferences = db.relationship(
        "Preferences",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

     # حذف البلاغات المرتبطة بالمستخدم تلقائيًا
    reports_made = db.relationship(
        "Report",
        foreign_keys="[Report.reporter_id]",
        back_populates="reporter",
        cascade="all, delete-orphan"
    )

    reports_received = db.relationship(
        "Report",
        foreign_keys="[Report.reported_user_id]",
        back_populates="reported_user",
        cascade="all, delete-orphan"
    )

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    program = db.Column(db.String(100), nullable=False)



class PreferenceCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    preference_id = db.Column(
        db.Integer,
        db.ForeignKey("preferences.id"),
        nullable=False
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False
    )

    cross_section = db.Column(db.Boolean, default=False)
    section = db.Column(db.String(10))

    preference = db.relationship(
        "Preferences",
        back_populates="courses"
    )

    course = db.relationship("Course")


class Preferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    country_code = db.Column(db.String(5))

    gpa = db.Column(db.Float, nullable=False)
    program = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.Integer)

    commitment_level = db.Column(db.Integer)


    courses = db.relationship(
    "PreferenceCourse",
    back_populates="preference",
    cascade="all, delete-orphan"
)



COMMITMENT_LEVELS = {
    1: "متفرّغ فقط قبل التسليم",
    2: "العمل مرة أسبوعياً",
    3: "عدة مرات أسبوعياً",
    4: "يومياً",
    5: "متفرغ بالكامل"
}

def commitment_level_label(level):
    return COMMITMENT_LEVELS.get(level, "غير محدد")

class CollaborationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sender = db.relationship("User", foreign_keys=[sender_id])
    
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver = db.relationship("User",foreign_keys=[receiver_id],backref="received_requests")

    status = db.Column(db.String(20), default="pending")  
    # pending | accepted | rejected

    created_at = db.Column(db.DateTime, server_default=db.func.now())


class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user1_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=db.func.now())
    last_activity = db.Column(db.DateTime, default=db.func.now())

    user1 = db.relationship("User", foreign_keys=[user1_id])
    user2 = db.relationship("User", foreign_keys=[user2_id])
    def other_user(self, my_id):
        return self.user2 if self.user1_id == my_id else self.user1
    
    
    @property
    def last_message(self):
        return (
            Message.query
            .filter_by(chat_id=self.id)
            .order_by(Message.created_at.desc())
            .first()
        )
    


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    chat_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_room.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship("User")
    chat = db.relationship("ChatRoom", backref="messages")

    def other_user(self, my_id): return self.user1 if self.user2_id == my_id else self.user2

    @property
    def last_message(self):
        return (
            Message.query
            .filter_by(chat_id=self.id)
            .order_by(Message.created_at.desc())
            .first()
        )

    def unread_count(self, user_id):
        return Message.query.filter(
            Message.chat_id == self.id,
            Message.sender_id != user_id,
            Message.is_read == False
        ).count()


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reported_user = db.relationship("User", foreign_keys=[reported_user_id])

    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.now())

    report_messages = db.relationship(
        "ReportMessage",
        back_populates="report",
        cascade="all, delete-orphan"
    )

    # convenience property
    @property
    def messages(self):
        return [rm.message for rm in self.report_messages if rm.message is not None]



class ReportMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    report_id = db.Column(
        db.Integer,
        db.ForeignKey('report.id'),
        nullable=False
    )

    message_id = db.Column(
        db.Integer,
        db.ForeignKey('message.id'),
        nullable=False
    )

    report = db.relationship("Report", back_populates="report_messages")
    message = db.relationship("Message")



class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    blocker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=db.func.now())


class AlgorithmSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gpa_weight = db.Column(db.Float, default=25)
    commitment_weight = db.Column(db.Float, default=20)
    age_weight = db.Column(db.Float, default=10)
    year_weight = db.Column(db.Float, default=10)

    courses_weight = db.Column(db.Float, default=35)
    max_courses = db.Column(db.Float, default=5)


def seed_algorithm_settings():
    existing = AlgorithmSettings.query.first()

    if not existing:
        default_settings = AlgorithmSettings(
            gpa_weight=25,
            commitment_weight=20,
            age_weight=10,
            year_weight=10,
            courses_weight = 35,
            max_courses =5
        )
        db.session.add(default_settings)
        db.session.commit()
        print("Default algorithm settings created.")
    else:
        print("Algorithm settings already exist.")