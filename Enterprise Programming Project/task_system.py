from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, task, status):
        pass

class User(Observer):
    def __init__(self, name):
        self.name = name

    def update(self, task, status):
        print(f"{self.name} notified: Task '{task}' status changed to {status}")

class Task:
    def __init__(self, name):
        self.name = name
        self.status = "Not Started"
        self.observers = []

    def attach(self, observer):
        self.observers.append(observer)

    def notify(self):
        for observer in self.observers:
            observer.update(self.name, self.status)

    def set_status(self, status):
        self.status = status
        self.notify()

class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.tasks = []
        return cls._instance

if __name__ == "__main__":
    user1 = User("Jordan")
    user2 = User("Alex")
    
    task1 = Task("Design")
    task2 = Task("Review")
    
    task1.attach(user1)
    task2.attach(user2)
    
    task1.set_status("In Progress")
    task2.set_status("Completed")