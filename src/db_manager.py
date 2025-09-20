import os
import psycopg2
from psycopg2 import sql
from psycopg2.errors import UndefinedTable, UndefinedColumn, UniqueViolation, DuplicateTable
from psycopg2.extras import RealDictCursor
from src.api_handler import to_get_10_employers
from src.vacancy_handler import VacHandler
from src.abstract_cls import AbcDBManager
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

class DBManager(AbcDBManager):
    """
    Класс работы с БД
    """

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.__conn = None
        self.__cur = None
        self.db_exists = True

        self.__conn_params = {
            'host': "localhost",
            'port': 5432,
            'dbname': db_name,
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '123456'),
            'options': '-c client_encoding=UTF8'
        }

    def __enter__(self):
        self.__connect()
        self.__cur = self.__conn.cursor(cursor_factory=RealDictCursor)
        return self

    def __connect(self):
        """ Метод для подключения к базе данных """
        try:
            self.__conn = psycopg2.connect(**self.__conn_params)
            self.__conn.autocommit = True
        except (psycopg2.Error, UnicodeDecodeError) as e:
            logging.error(f"Ошибка подключения: {e}")
            self.__conn_params['dbname'] = 'postgres'
            self.db_exists = False
            self.create_database()
            self.__connect()  # Повторное подключение к новой базе данных

    def create_database(self):
        """Создание базы данных"""
        try:
            with psycopg2.connect(**self.__conn_params) as err_conn:
                err_conn.autocommit = True
                with err_conn.cursor() as err_cur:
                    err_cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.db_name)))
        except psycopg2.Error as e:
            logging.error(f"Ошибка создания базы данных: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__cur:
            self.__cur.close()
        if self.__conn:
            if exc_type is None:
                self.__conn.commit()
            else:
                self.__conn.rollback()
            self.__conn.close()
            logging.info('Соединение отключено')

    def to_update_db(self):
        """ Метод обновления таблицы с вакансиями """
        try:
            self.__to_add_data(self.__cur)
            logging.info('Запись БД окончена')
        except (UndefinedTable, UndefinedColumn, UniqueViolation, DuplicateTable):
            logging.info('Обновление БД начато...')
            self.__cur.execute('DROP TABLE IF EXISTS vacancies;')
            self.__cur.execute('DROP TABLE IF EXISTS employers;')
            self.__to_add_data(self.__cur)
            logging.info('Обновление БД окончено')

    @staticmethod
    def __to_add_data(cur):
        """ Метод добавления данных в БД """
        cur.execute("""
            CREATE TABLE employers (
                employer_id INT,
                employer_name VARCHAR,
                comp_url VARCHAR,
                vacancies_url VARCHAR,
                rating REAL,
                employer_trusted BOOLEAN,
                CONSTRAINT pk_companies_company_id PRIMARY KEY (employer_id)
            );
        """)

        cur.execute("""
            CREATE TABLE vacancies (
                vacancy_id INT,
                vacancy_name VARCHAR,
                city VARCHAR,
                vacancy_url VARCHAR,
                schedule VARCHAR,
                vac_salary_from INT,
                vac_salary_to INT,
                vac_currency VARCHAR,
                vac_avg_salary INT,
                employer_id INT,
                CONSTRAINT pk_vacancies_vacancy_id PRIMARY KEY (vacancy_id),
                CONSTRAINT fk_employers_to_vacancies FOREIGN KEY (employer_id) REFERENCES employers(employer_id)
            );
        """)

        logging.info('Получение данных с HH.ru...')
        api_response = to_get_10_employers()
        logging.info('Данные получены.')

        vacancies = VacHandler()

        for vac in api_response:
            employer_field = vac['employer']
            emp_params = vacancies.to_give_emp_params(employer_field)

            comp_query = """
                        INSERT INTO employers 
                        (employer_id, employer_name, comp_url, vacancies_url, rating, employer_trusted)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (employer_id) DO NOTHING;
                        """
            cur.execute(comp_query, emp_params)

            vac_params = vacancies.to_give_vac_params(vac, emp_params)
            query = """
                    INSERT INTO vacancies (vacancy_id, vacancy_name, city, vacancy_url, schedule, vac_salary_from,
                    vac_salary_to, vac_currency, vac_avg_salary, employer_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (vacancy_id) DO UPDATE SET
                    vacancy_name = EXCLUDED.vacancy_name,
                    city = EXCLUDED.city,
                    vacancy_url = EXCLUDED.vacancy_url,
                    schedule = EXCLUDED.schedule,
                    vac_salary_from = EXCLUDED.vac_salary_from,
                    vac_salary_to = EXCLUDED.vac_salary_to,
                    vac_currency = EXCLUDED.vac_currency,
                    vac_avg_salary = EXCLUDED.vac_avg_salary,
                    employer_id = EXCLUDED.employer_id;
                    """
            cur.execute(query, vac_params)

    def get_companies_and_vacancies_count(self) -> list:
        """ Метод получения списка всех компаний и кол-ва их вакансий """
        self.__cur.execute("""
        SELECT COUNT(v.vacancy_id) AS vac_count, e.employer_id, e.employer_name
        FROM vacancies AS v
        JOIN employers AS e USING (employer_id)
        GROUP BY e.employer_id, e.employer_name
        ORDER BY vac_count DESC;
        """)

        return [dict(row) for row in self.__cur.fetchall()]

    def get_all_vacancies(self) -> list:
        """ Метод получения всех вакансий с указанием названия компании, названия вакансии, зп и ссылки на нее """
        self.__cur.execute("""
            SELECT e.employer_name, v.vacancy_name, v.vac_salary_from, v.vac_salary_to, v.vac_avg_salary, v.vacancy_url
            FROM vacancies AS v
            JOIN employers AS e USING (employer_id);
        """)

        return [dict(row) for row in self.__cur.fetchall()]

    def get_avg_salary(self) -> dict:
        """ Метод получения средней зп по вакансиям """
        self.__cur.execute("""
            SELECT AVG(vac_avg_salary) AS average_salary
            FROM vacancies;
        """)

        avg_salary = self.__cur.fetchone()
        avg_salary['average_salary'] = round(float(avg_salary['average_salary']), 2)

        return avg_salary

    def get_vacancies_with_higher_salary(self) -> list:
        """ Метод получения списка вакансий, зп которых выше среднего по вакансиям """
        self.__cur.execute("""
            SELECT *
            FROM vacancies
            WHERE vac_avg_salary > (SELECT AVG(vac_avg_salary) FROM vacancies);
        """)

        return [dict(row) for row in self.__cur.fetchall()]

    def get_vacancies_with_keyword(self, keyword: str) -> list | None:
        """ Метод получения всех вакансий по ключевому слову """
        if isinstance(keyword, str):
            self.__cur.execute("""
                SELECT *
                FROM vacancies
                WHERE vacancy_name ILIKE %s;""", (f'%{keyword}%',))

            return [dict(row) for row in self.__cur.fetchall()]

#print(f"DB_USER: {os.getenv('DB_USER')}")
#print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")