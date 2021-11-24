#!/usr/bin/python
import datetime, requests, sys, json, inquirer, urllib


# Entry in the timesheet
class OperateEntry:

    date = None
    duration = None
    client = None
    project = None
    task = None
    rate = 0
    billable = 0

    def __init__(self, date, duration, client=None, project=None, task=None):
        self.date = date
        self.duration = duration
        self.client = client
        self.project = project
        self.task = task

    def date_end(self):
        return self.date + datetime.timedelta(hours=self.duration)


class OperateTimesheet:

    entries = []
    employee_mail = None
    employee_name = None
    employee_id = None
    company = None
    recent_entry = None

    def __init__(self, employee_id, employee_name, employee_mail, company):
        self.employee_id = employee_id
        self.employee_mail = employee_mail
        self.employee_name = employee_name
        self.company = company

    def add_entry(self, entry: OperateEntry):
        if not self.recent_entry or self.recent_entry.date < entry.date:
            self.recent_entry = entry

        self.entries.append(entry)

    def as_object(self):

        timesheet_name = "New Timesheet {}".format(self.recent_entry.date)

        data = {
            "docstatus": 0,
            "doctype": "Timesheet",
            "naming_series": "TS-.YYYY.-",
            "__islocal": 1,
            "__unsaved": 1,
            "status": "Draft",

            "name": timesheet_name,
            "owner": self.employee_mail,
            "employee": self.employee_id,
            "employee_name": self.employee_name,
            "company": self.company,
            "department": None,

            "note": "<div>{}<br />{}</div>".format(
                "Imported automatically from Toggl",
                "Most recent entry for this timesheet: {}".format(self.recent_entry.date)
            ),
            "time_logs": [],

            "total_hours": 0,
            "total_billable_amount": 0,
            "total_billable_hours": 0,
            "total_costing_amount": 0,
        }

        entries = []
        for (i, entry) in enumerate(self.entries):

            idx = i+1


            billable = 1 if entry.rate else 0

            """
            NOT SUMMED IN API CALL
            data['total_hours'] += entry.duration
            data['total_billable_hours'] += billable * entry.duration
            data['total_billable_amount'] += data['total_billable_hours'] * entry.rate
            data['total_costing_amount'] += 0
            """

            entry_data = {
                "docstatus": 0,
                "doctype": "Timesheet Detail",
                "__islocal": 1,
                "__unsaved": 1, "owner": self.employee_mail,

                "idx": idx,
                "name": "New Timesheet Detail {}".format(idx),

                "completed": 0,
                "billing_amount": 0,
                "costing_amount": 0,
                "parent": timesheet_name,
                "parentfield": "time_logs",
                "parenttype": "Timesheet",

                "from_time": entry.date.strftime('%Y-%m-%d %H:%M:%S'),
                "to_time": entry.date_end().strftime('%Y-%m-%d %H:%M:%S'),
                "hours": round(entry.duration, 2),

                "project": entry.client,
                "activity_type": entry.project,
                "billing_rate": entry.rate,
                "billable": billable,
                "costing_rate": 0, # Not treated yet

                "ts_description": entry.task,
            }

            entries.append(entry_data)


        data["time_logs"] = entries

        return data


# The client that will interact with the timesheet
class OperateClient:

    domain = None
    employee_mail = None
    employee_name = None
    employee_id = None
    company_name = None
    cookies = None
    entries = []

    filename = './matches.json'

    matches = {}
    existing = {
        "clients": [],
        "projects": [],
    }
    timesheet = None
    rates = {}
    billable = {}


    def __init__(self, domain, usermail, password):
        self.domain = domain
        self.employee_mail = usermail
        self.__login(usermail, password)
        self.__init_timesheet()

    # API

    def __operate_error(self, text):
        print("Operate error", text)
        sys.exit()

    def __get(self, path):
        return requests.get("{}{}".format(self.domain, path), cookies=self.cookies)

    def __post(self, path, data=""):
        return requests.post("{}{}".format(self.domain, path), data, cookies=self.cookies, headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        })

    # Login

    def __login(self, usermail, password):
        t = self.__post("/", "cmd=login&usr={usr}&pwd={pwd}&device=desktop".format(usr=usermail, pwd=password))
        try:
            self.employee_name = t.json()['full_name']
            print("Connected as {user}".format(user=self.employee_name))
            self.cookies = t.cookies
            self.__load_user_data()
            return True;
        except KeyError:
            self.__operate_error("Wrong credentiels")
        except Exception:
            self.__operate_error("Unknown exception")

    def is_logged_in(self):
        return self.cookies is not None

    def __load_user_data(self):
        t = self.__get(
            "/api/method/frappe.client.get_value?doctype=Employee&fieldname=%5B%22name%22%2C%22company%22%5D&filters=%7B%22user_id%22%3A%22{email}%22%7D&_=1637638112873".format(email=self.employee_mail)
        ).json()['message']
        self.employee_id = t['name']
        self.company_name = t['company']
        print("Employee:", self.company_name, self.employee_id)

    # Tags matching

    def __load_config(self):

        # Existing matches
        try:
            f = open(self.filename)
            self.matches = json.load(f)
        except FileNotFoundError:
            self.matches = {}
        except json.JSONDecodeError:
            print("Invalid JSON, please correct it")
            sys.exit(1)

    def __save_config(self):
        with open(self.filename, 'w') as f:
            json.dump(self.matches, f)

    def __get_config_in(self, index, value, prompt, search_string):

        if index not in self.matches:
            self.matches[index] = {}

        # If existing in matches file
        if value in self.matches[index]:
            return self.matches[index][value]

        response = None
        new_search = "- Search for a new keyword -"
        while response is None:

            text = inquirer.prompt([
                inquirer.Text('search', message=prompt),
            ])['search']

            choices = []
            r = self.__post("/api/method/frappe.desk.search.search_link",
                            search_string.format(keyword=text)).json()
            for result in r['results']:
                choices.append(result['value'])

            if not len(choices):
                print("No result for '{}'".format(text))
            else:
                choices.append(new_search)

                # Creating new matching
                answers = inquirer.prompt([
                    inquirer.List(
                        index,
                        message="Pick one: {}".format(prompt),
                        choices=choices
                    ),
                ])
                response = answers[index]
                if response == new_search:
                    response = None

        self.matches[index][value] = response
        self.__save_config()
        return response

    def __get_client_for(self, value):
        return self.__get_config_in(
            'clients', value,
            "Who is the client '{}'?".format(value),
            "txt={keyword}&doctype=Project&ignore_user_permissions=0&reference_doctype=Timesheet+Detail&filters=%7B%22company%22%3A%22{company}%22%7D".format(keyword="{keyword}",company=self.company_name)
        )

    def __get_project_for(self, value):
        return self.__get_config_in(
            'projects', value,
            "Which kind of task is '{}'?".format(value),
            "txt={keyword}&doctype=Activity+Type&ignore_user_permissions=0&reference_doctype=Timesheet+Detail"
        )

    # Not used yet. Only the tasks with an hourly rate are considered as billed.
    def __get_is_billable_for(self, project, client=None):

        if project in self.billable:
            return self.billable[project]

        t = self.__post(
            "/api/method/erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
            "employee={employee_id}&activity_type={project}".format(employee_id=self.employee_id, project=project)
        )
        print(t.json()['message'])
        billable = 0

        self.billable[project] = billable
        return billable

    def __get_rate_for(self, client, project):

        id = "{} --- {}".format(client, project)

        if id in self.rates:
            return self.rates[id]

        t = self.__post(
            "/api/method/nothing.nothing.utils.get_billing_rate",
            "project={client}&activity_type={project}&employee={employee_id}".format(
                employee_id=self.employee_id,
                project=project,
                client=client
            )
        )
        rate = t.json()['message']

        self.rates[id] = rate
        return rate




    # Timesheet manipulations

    def __init_timesheet(self):
        self.entries = []
        self.timesheet = OperateTimesheet(
            employee_id=self.employee_id,
            employee_name=self.employee_name,
            employee_mail=self.employee_mail,
            company=self.company_name)

    def __add_entry_to_timesheet(self, entry: OperateEntry):

        # Adjusting with Operate data
        entry.client = self.__get_client_for(entry.client)
        entry.project = self.__get_project_for(entry.project)
        entry.rate = self.__get_rate_for(project=entry.project, client=entry.client)
        # entry.billable = self.__get_is_billable_for(project=entry.project, client=entry.client)

        self.timesheet.add_entry(entry)

    def __save_timesheet(self):

        data = self.timesheet.as_object()
        t = self.__post(
            "/api/method/frappe.desk.form.save.savedocs",
            urllib.parse.urlencode({
                "doc": json.dumps(data, separators=(',', ':')),
                "action": "Save"
            })
        )
        print("Exported:", t.status_code == 200)




    # Public data

    def add_entry(self, entry: OperateEntry):
        self.entries.append(entry)
        return self

    def submit(self):
        self.__load_config()
        self.__adjust_entries_overlap(self.entries)
        for entry in self.entries:
            self.__add_entry_to_timesheet(entry)
        self.__save_timesheet()

        # Reset
        self.__init_timesheet()



    # Adjust overlap

    def __adjust_entries_overlap(self, entries):

        entries.sort(key=lambda e: e.date)

        for index_a, a in enumerate(entries):
            for index_b, b in enumerate(entries):
                if index_a < index_b:
                    if self.__adjust_specific_entry_overlap(a, b):
                        print("Adjusted")
                        # Start again after adjustment
                        return self.__adjust_entries_overlap(entries)

        return entries


    def __adjust_specific_entry_overlap(self, a: OperateEntry, b: OperateEntry):

        if a == b:
            return False

        if a.date_end() >= b.date:
            b.date = a.date_end() + datetime.timedelta(seconds=1)

            return True

        return False
