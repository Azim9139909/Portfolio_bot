import sqlite3
from config import DATABASE

skills = [ (_,) for _ in (['Python', 'SQL', 'API', 'Telegram', 'HTML', 'CSS', 'FLASK', 'AI'])]
statuses = [(_,) for _ in (['На этапе проектирования', 'В процессе разработки',
                            'Разработан. Готов к использованию.', 'Обновлен',
                            'Завершен. Не поддерживается'])]


class DB_Manager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS status (
                status_id INTEGER PRIMARY KEY,
                status_name TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                project_name TEXT NOT NULL,
                description TEXT,
                url TEXT,
                status_id INTEGER,
                FOREIGN KEY (status_id) REFERENCES status(status_id))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS skills (
                skill_id INTEGER PRIMARY KEY,
                skill_name TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS project_skills (
                project_id INTEGER,
                skill_id INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id))''')
            conn.commit()

    def __executemany(self, sql, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(sql, data)
            conn.commit()

    def __select_data(self, sql, data=tuple()):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(sql, data)
            return cur.fetchall()

    def default_insert(self):
        sql = 'INSERT INTO skills (skill_name) VALUES (?)'
        self.__executemany(sql, skills)
        sql = 'INSERT INTO status (status_name) VALUES (?)'
        self.__executemany(sql, statuses)

    # Добавить проект
    def insert_project(self, data):
        sql = 'INSERT INTO projects (user_id, project_name, url, status_id) VALUES (?, ?, ?, ?)'
        self.__executemany(sql, data)

    # Добавить навык к проекту
    def insert_skill(self, user_id, project_name, skill):
        sql = 'SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?'
        project_id = self.__select_data(sql, (project_name, user_id))[0][0]
        skill_id = self.__select_data('SELECT skill_id FROM skills WHERE skill_name = ?', (skill,))[0][0]
        sql = 'INSERT OR IGNORE INTO project_skills VALUES (?, ?)'
        self.__executemany(sql, [(project_id, skill_id)])

    # Все статусы
    def get_statuses(self):
        return self.__select_data('SELECT status_name FROM status')

    # ID статуса по названию
    def get_status_id(self, status_name):
        res = self.__select_data('SELECT status_id FROM status WHERE status_name = ?', (status_name,))
        return res[0][0] if res else None

    # Все проекты пользователя
    def get_projects(self, user_id):
        return self.__select_data('SELECT * FROM projects WHERE user_id = ?', (user_id,))

    # ID проекта по названию
    def get_project_id(self, project_name, user_id):
        sql = 'SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?'
        return self.__select_data(sql, (project_name, user_id))[0][0]

    # Все навыки
    def get_skills(self):
        return self.__select_data('SELECT * FROM skills')

    # Навыки конкретного проекта
    def get_project_skills(self, project_name):
        sql = '''SELECT skill_name FROM projects
                 JOIN project_skills ON projects.project_id = project_skills.project_id
                 JOIN skills ON skills.skill_id = project_skills.skill_id
                 WHERE project_name = ?'''
        res = self.__select_data(sql, (project_name,))
        return ', '.join([x[0] for x in res])

    # Информация о проекте со статусом
    def get_project_info(self, user_id, project_name):
        sql = '''SELECT project_name, description, url, status_name FROM projects
                 JOIN status ON status.status_id = projects.status_id
                 WHERE project_name = ? AND user_id = ?'''
        return self.__select_data(sql, (project_name, user_id))

    # Изменить поле проекта
    def update_projects(self, param, data):
        sql = f'UPDATE projects SET {param} = ? WHERE project_name = ? AND user_id = ?'
        self.__executemany(sql, [data])

    # Удалить проект
    def delete_project(self, user_id, project_id):
        sql = 'DELETE FROM projects WHERE user_id = ? AND project_id = ?'
        self.__executemany(sql, [(user_id, project_id)])

    # Удалить навык у проекта
    def delete_skill(self, project_id, skill_id):
        sql = 'DELETE FROM project_skills WHERE skill_id = ? AND project_id = ?'
        self.__executemany(sql, [(skill_id, project_id)])


if __name__ == '__main__':
    manager = DB_Manager(DATABASE)
    manager.create_tables()
    manager.default_insert()

    user_id = 1

    # статусы из txt → статусы в базе данных
    status_map = {
        'Проектирование': 'На этапе проектирования',
        'В процессе разработки': 'В процессе разработки',
        'Разработан': 'Разработан. Готов к использованию.',
        'Обновлен': 'Обновлен',
        'Завершен/Не поддерживается': 'Завершен. Не поддерживается',
    }
    all_skills = [s[1] for s in manager.get_skills()]

    # читаем projects.txt и собираем проекты
    projects = []
    current = {}
    with open('projects.txt', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if ': ' not in line:
                continue
            key, value = line.split(': ', 1)
            if key == 'Название проекта':
                current = {'name': value}
                projects.append(current)
            elif key == 'Описание проекта':
                current['description'] = value
            elif key == 'Ссылка на гитхаб репозиторий проекта':
                current['url'] = value
            elif key == 'Статус проекта':
                current['status'] = value
            elif key.startswith('Навыки'):
                current['skills'] = value.split(', ')

    # добавляем всё в базу данных
    for p in projects:
        status_id = manager.get_status_id(status_map[p['status']])
        manager.insert_project([(user_id, p['name'], p['url'], status_id)])
        manager.update_projects('description', (p['description'], p['name'], user_id))
        for skill in p['skills']:
            if skill in all_skills:  # Lua и т.п. пропускаем
                manager.insert_skill(user_id, p['name'], skill)

    print('Добавлено проектов:', len(manager.get_projects(user_id)))
    print(manager.get_project_info(user_id, 'HomeworkBuddy'))
    print(manager.get_project_skills('HomeworkBuddy'))
