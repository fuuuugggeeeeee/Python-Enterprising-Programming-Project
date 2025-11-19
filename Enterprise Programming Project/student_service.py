class StudentMicroservice:
    def __init__(self):
        self.students = {}

    def add_student(self, student_id, name, course):
        if student_id in self.students:
            print("Student ID already exists!")
            return
        
        self.students[student_id] = {"name": name, "course": course}
        print("Student added successfully!")

    def get_student(self, student_id):
        student = self.students.get(student_id)
        if student:
            print(f"Student ID: {student_id}")
            print(f"Name: {student['name']}")
            print(f"Course: {student['course']}")
        else:
            print("Student not found!")

def run_console():
    service = StudentMicroservice()
    
    while True:
        print("\n===== Student Service =====")
        print("1. Add Student")
        print("2. Get Student")
        print("3. Exit")
        
        choice = input("Choose option (1-3): ")
        
        if choice == "1":
            sid = input("Enter Student ID: ")
            name = input("Enter Name: ")
            course = input("Enter Course: ")
            service.add_student(sid, name, course)
        elif choice == "2":
            sid = input("Enter Student ID: ")
            service.get_student(sid)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    run_console()