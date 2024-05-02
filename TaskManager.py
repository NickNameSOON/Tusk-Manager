import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup

class TaskManager(App):
    def build(self):
        self.conn = sqlite3.connect('tasks.db')
        self.create_table()

        # Create screen manager
        self.sm = ScreenManager()

        # Main screen with task list
        main_screen = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical')

        self.task_list_layout = BoxLayout(orientation='vertical', spacing=5)
        main_layout.add_widget(self.task_list_layout)

        new_task_button = Button(text='Add New Task', size_hint_y=None, height=40)
        new_task_button.bind(on_press=self.go_to_new_task_screen)
        main_layout.add_widget(new_task_button)

        main_screen.add_widget(main_layout)
        self.sm.add_widget(main_screen)

        # New task screen
        new_task_screen = Screen(name='new_task')
        new_task_layout = BoxLayout(orientation='vertical')

        self.task_input = TextInput(hint_text='Enter new task...')
        new_task_layout.add_widget(self.task_input)

        save_button = Button(text='Save Task')
        save_button.bind(on_press=self.save_task)
        new_task_layout.add_widget(save_button)

        new_task_screen.add_widget(new_task_layout)
        self.sm.add_widget(new_task_screen)

        self.update_task_list()  # Update task list initially

        return self.sm

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           description TEXT,
                           status TEXT)''')
        self.conn.commit()

    def go_to_new_task_screen(self, instance):
        self.sm.current = 'new_task'

    def save_task(self, instance):
        task_text = self.task_input.text.strip()
        if task_text:
            cursor = self.conn.cursor()
            cursor.execute('''INSERT INTO tasks (description, status) VALUES (?, ?)''', (task_text, 'active'))
            self.conn.commit()
            self.task_input.text = ''
            self.update_task_list()
            # Switch back to main screen
            self.sm.current = 'main'

    def update_task_list(self):
        cursor = self.conn.cursor()
        cursor.execute('''SELECT id, description, status FROM tasks''')
        tasks = cursor.fetchall()
        self.task_list_layout.clear_widgets()
        for task in tasks:
            task_id, task_description, task_status = task
            task_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)

            task_checkbox = CheckBox()
            task_checkbox.task_id = task_id
            task_checkbox.bind(active=self.on_checkbox_active)
            task_layout.add_widget(task_checkbox)

            task_label = Label(text=task_description, size_hint_x=0.8, font_size=18)
            task_layout.add_widget(task_label)

            if task_status == 'active':
                task_label.color = (1, 1, 1, 1)
            elif task_status == 'completed':
                task_label.color = (0, 1, 0, 1)

            self.task_list_layout.add_widget(task_layout)

    def on_checkbox_active(self, checkbox, value):
        if value:
            if not hasattr(self, 'selected_tasks'):
                self.selected_tasks = set()
            self.selected_tasks.add(checkbox.task_id)
            self.show_action_buttons()
        else:
            if hasattr(self, 'selected_tasks') and checkbox.task_id in self.selected_tasks:
                self.selected_tasks.remove(checkbox.task_id)
                if not self.selected_tasks:
                    self.hide_action_buttons()

    def show_action_buttons(self):
        if not hasattr(self, 'action_buttons_layout'):
            self.action_buttons_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)

            change_status_button = Button(text='Change Status')
            change_status_button.bind(on_press=self.change_status)
            self.action_buttons_layout.add_widget(change_status_button)

            delete_button = Button(text='Delete')
            delete_button.bind(on_press=self.delete_tasks)
            self.action_buttons_layout.add_widget(delete_button)

            edit_button = Button(text='Edit')
            edit_button.bind(on_press=self.edit_selected_task)
            self.action_buttons_layout.add_widget(edit_button)

            self.task_list_layout.add_widget(self.action_buttons_layout)

    def hide_action_buttons(self):
        if hasattr(self, 'action_buttons_layout'):
            self.task_list_layout.remove_widget(self.action_buttons_layout)
            delattr(self, 'action_buttons_layout')

    def change_status(self, instance):
        cursor = self.conn.cursor()
        for task_id in self.selected_tasks:
            cursor.execute('''SELECT status FROM tasks WHERE id=?''', (task_id,))
            current_status = cursor.fetchone()[0]
            new_status = 'completed' if current_status == 'active' else 'active'
            cursor.execute('''UPDATE tasks SET status=? WHERE id=?''', (new_status, task_id))
        self.conn.commit()
        self.update_task_list()
        self.selected_tasks.clear()
        self.hide_action_buttons()

    def delete_tasks(self, instance):
        cursor = self.conn.cursor()
        for task_id in self.selected_tasks:
            cursor.execute('''DELETE FROM tasks WHERE id=?''', (task_id,))
        self.conn.commit()
        self.update_task_list()
        self.selected_tasks.clear()
        self.hide_action_buttons()

    def edit_selected_task(self, instance):
        if len(self.selected_tasks) == 1:
            task_id = next(iter(self.selected_tasks))
            cursor = self.conn.cursor()
            cursor.execute('''SELECT description, status FROM tasks WHERE id=?''', (task_id,))
            task_description, task_status = cursor.fetchone()
            popup = EditTaskPopup(task_id, task_description, task_status, self.update_task)
            popup.open()
        else:
            # Show error message if more than one task is selected
            self.show_error_message('Please select only one task to edit.')

    def edit_task_popup(self, instance, touch):
        if touch.is_mouse_scrolling or not instance.collide_point(*touch.pos):
            return

        # Отримати перший дочірній елемент, який є CheckBox
        task_checkbox = [child for child in instance.children if isinstance(child, CheckBox)][0]
        task_id = task_checkbox.task_id
        cursor = self.conn.cursor()
        cursor.execute('''SELECT description, status FROM tasks WHERE id=?''', (task_id,))
        task_description, task_status = cursor.fetchone()
        popup = EditTaskPopup(task_id, task_description, task_status, self.update_task)
        popup.open()

    def update_task(self, task_id, new_description, new_status):
        cursor = self.conn.cursor()
        cursor.execute('''UPDATE tasks SET description=?, status=? WHERE id=?''', (new_description, new_status, task_id))
        self.conn.commit()
        self.update_task_list()

    def show_error_message(self, message):
        popup = Popup(title='Error', content=Label(text=message), size_hint=(None, None), size=(300, 200))
        popup.open()

class EditTaskPopup(Popup):
    def __init__(self, task_id, task_description, task_status, update_callback, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.update_callback = update_callback

        self.title = 'Edit Task'

        self.task_description_input = TextInput(text=task_description, hint_text='Enter task description...')
        self.status_checkbox = CheckBox(active=(task_status == 'completed'))
        self.status_label = Label(text='Completed')

        button_layout = BoxLayout(orientation='horizontal')
        save_button = Button(text='Save', size_hint_x=0.5)
        save_button.bind(on_press=self.save_task)
        cancel_button = Button(text='Cancel', size_hint_x=0.5)
        cancel_button.bind(on_press=self.dismiss)

        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)

        self.content = BoxLayout(orientation='vertical')
        self.content.add_widget(self.task_description_input)
        self.content.add_widget(self.status_checkbox)
        self.content.add_widget(self.status_label)
        self.content.add_widget(button_layout)

    def save_task(self, instance):
        new_description = self.task_description_input.text.strip()
        new_status = 'completed' if self.status_checkbox.active else 'active'
        self.update_callback(self.task_id, new_description, new_status)
        self.dismiss()


if __name__ == '__main__':
    TaskManager().run()
