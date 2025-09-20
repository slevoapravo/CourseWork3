from src.db_manager import DBManager


def main():
    """
    Функция взаимодействия с пользователем
    """

    print(
        'Привет!\n'
        'Перед тобой программа взаимодействия с БД.\n'
        'Программа автоматически создает (если БД не существовало) и подключается к БД.\n'
        'БД представляет из себя вакансии от 10 разных компаний с HH.ru\n'
    )

    incorrect_input = True
    db_name = ''
    while incorrect_input:
        db_name = input('Введите имя БД. Это должна быть строка(буквы и/или цифры) без знаков:\n').strip()
        if db_name and (db_name.isalnum() or '_' in db_name):
            incorrect_input = False
            print(f'Отлично! Имя для БД - {db_name}\n')
        else:
            print('Только буквы и цифры. Давай еще раз.')

    with DBManager(db_name) as db:
        if db.db_exists:
            rewrite = input("Похоже, такая БД существует, обновить последние данные?\nда/нет\n").lower()
            while rewrite not in ['да', 'нет']:
                print('Ответ должен быть либо "да", либо "нет".')
                rewrite = input("да/нет\n").lower()

            if rewrite == 'да':
                db.to_update_db()
                print('БД обновлена')
            else:
                print('БД не обновлена')
        else:
            db.to_update_db()

        # 1. Получение списка всех компаний и кол-ва их вакансий
        print('Сейчас продемонстрирую функционал:\n'
              '---1. Получение списка всех компаний и кол-ва их вакансий---\n')
        data = db.get_companies_and_vacancies_count()
        for elem in data:
            print(f'Название компании: {elem["employer_name"]}. Коллтчество вакансий: {elem["vac_count"]}')
            print("-" * 50)

        # 2. Получение всех вакансий с указанием названия компании, названия вакансии, зп и ссылки на нее
        print('---2. Получение всех вакансий с указанием названия компании, названия вакансии, зп и ссылки на нее---\n')
        data = db.get_all_vacancies()
        for elem in data:
            salary = elem.get("salary", "Не указана")  # Используем метод get для безопасного доступа к ключу
            print(
                f'Компания: {elem["employer_name"]}, Вакансия: {elem["vacancy_name"]}, Зарплата: {salary}, Ссылка: {elem["vacancy_url"]}')
            print("-" * 50)

        # 3. Получение средней зп по вакансиям
        print('---3. Получение средней зп по вакансиям---\n')
        avg_salary = db.get_avg_salary()
        print(f'Средняя зарплата по вакансиям: {avg_salary}\n')

        # 4. Получение списка вакансий, зп которых выше среднего по вакансиям
        print('---4. Получение списка вакансий, зп которых выше среднего по вакансиям---\n')
        data = db.get_vacancies_with_higher_salary()
        for elem in data:
            employer_name = elem.get("employer_name", "Не указана")
            vacancy_name = elem.get("vacancy_name", "Не указана")
            salary = elem.get("salary", "Не указана")
            vacancy_url = elem.get("vacancy_url", "Не указана")
            print(f'Компания: {employer_name}, Вакансия: {vacancy_name}, Зарплата: {salary}, Ссылка: {vacancy_url}')
            print("-" * 50)

        # 5.1 Получение всех вакансий по ключевому слову (допустим "Чат")
        print('---5.1 Получение всех вакансий по ключевому слову (допустим "Чат")---\n')
        data = db.get_vacancies_with_keyword("Чат")
        for elem in data:
            print(
                f'Компания: {elem["employer_name"]}, Вакансия: {elem["vacancy_name"]}, Зарплата: {elem["salary"]}, Ссылка: {elem["vacancy_url"]}')
            print("-" * 50)

        # 5.2 Получение всех вакансий по ключевому слову (допустим "Космонавт")
        print('---5.2 Получение всех вакансий по ключевому слову (допустим "Космонавт")---\n')
        data = db.get_vacancies_with_keyword("Космонавт")
        for elem in data:
            print(
                f'Компания: {elem["employer_name"]}, Вакансия: {elem["vacancy_name"]}, Зарплата: {elem["salary"]}, Ссылка: {elem["vacancy_url"]}')
            print("-" * 50)


if __name__ == '__main__':
    main()