#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from pathlib import Path
from time import sleep
import config
import random
import csv

class Bot:
    def __init__(self, username, password):
        self.username = username
        self.password = password

        opts = Options()
        #opts.headless = True
        opts.add_argument('--disable-extensions')
        self.ffdriver = webdriver.Firefox(options=opts, executable_path=Path('./bin/geckodriver'))
        self.current_results_page = 1

    def login(self):
        self.ffdriver.get('https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin')
        input_username = self.ffdriver.find_element_by_id('username')
        input_password = self.ffdriver.find_element_by_id('password')
        input_username.send_keys(self.username)
        input_password.send_keys(self.password)

        btn_submit = self.ffdriver.find_element_by_xpath('//button[@type="submit"]')
        btn_submit.click()

    def search_jobs(self, search_string, location = 'United States'):
        self.ffdriver.get('https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=' + search_string + '&sortBy=DD')

    def get_job_ids(self):
        self.load_results()

        results = self.ffdriver.find_elements_by_xpath('//div[@data-job-id]')

        ids = []

        for el in results:
            try:
                ids.append(el.get_attribute('data-job-id').split(':')[-1])
            except NoSuchElementException:
                print('company name not found')

        return ids

    def next_page(self):
        self.current_results_page += 1
        try:
            btn = self.ffdriver.find_element_by_xpath('//button[@aria-label="Page ' + str(self.current_results_page) + '"]')
            btn.click()
            return True
        except NoSuchElementException:
            return False

    def write_job_to_csv(self, job):
        filename = 'jobs.csv'
        file_exists = Path(filename).exists()

        with open(filename, mode='a') as csv_file:
            fieldnames = ['id', 'applied', 'company', 'title', 'location', 'description']
            writer = csv.DictWriter(csv_file, fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(job)
    
    def load_results(self):
        # Scroll to bottom of search results to load them all
        scroll_top = 0
        scroll_amt = 40
        div_results = self.ffdriver.find_element_by_xpath('//div[contains(@class, "jobs-search-results")]')
        scroll_height = self.ffdriver.execute_script('return arguments[0].scrollHeight', div_results)
        while scroll_top < scroll_height + scroll_amt:
            self.ffdriver.execute_script('arguments[0].scrollTop = ' + str(scroll_top) + ';', div_results)
            scroll_top += scroll_amt;
            sleep(0.1)

    def apply(self, job_id):
        self.ffdriver.get('https://www.linkedin.com/jobs/view/' + str(job_id))

        try:
            job_title = self.ffdriver.find_element_by_xpath('//h1[contains(@class, "job-title")]').text
        except NoSuchElementException:
            job_title = 'Title not found'

        try:
            job_location = self.ffdriver.find_element_by_xpath('//span[@class="a11y-text"][text()="Company Location"]/following-sibling::span').text
        except NoSuchElementException:
            job_location = 'Location not found'

        try:
            job_description = self.ffdriver.find_element_by_id('job-details').text
        except NoSuchElementException:
            job_description = 'Description not found'

        try:
            job_company = self.ffdriver.find_element_by_xpath('//span[@class="a11y-text"][text()="Company Name"]/following-sibling::a').text
        except NoSuchElementException:
            job_company = 'Company name not found'

        job = {'id': job_id, 'applied': False, 'company': job_company, 'title': job_title, 'location': job_location, 'description': job_description}

        try:
            btn = self.ffdriver.find_element_by_xpath('//button[span[text()="Easy Apply"]]')
            btn.click()
        except NoSuchElementException:
            print('Could not find Easy Apply button')
            return

        # Was a new tab opened?
        is_simple = len(self.ffdriver.window_handles) == 1

        if not is_simple:
            # Just close the tab for now and skip the application
            self.ffdriver.switch_to_window(self.ffdriver.window_handles[1])
            self.ffdriver.close()
            self.ffdriver.switch_to_window(self.ffdriver.window_handles[0])
            self.write_job_to_csv(job)
            #print('Not simple')
            return

        if is_simple:
            try:
                # Uncheck follow company
                btn = self.ffdriver.find_element_by_xpath('//label[contains(@class, "follow-company-label")]')
                btn.click()
            except NoSuchElementException:
                pass

            try:
                self.ffdriver.find_element_by_xpath('//button[text()="Continue"]')
                # For now just close the tab if it is not a one-page application
                self.ffdriver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 'w')
            except NoSuchElementException:
                pass


            # Submit application
            try:
                btn = self.ffdriver.find_element_by_xpath('//button[span[text()="Submit application"]]')
                btn.click()
                job['applied'] = True
                self.write_job_to_csv(job)
            except NoSuchElementException:
                return

def is_id_in_csv(job_id):
    with open('jobs.csv', mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if job_id == row['id']:
                return True
        return False

def main():
    bot = Bot(config.username, config.password)
    bot.ffdriver.implicitly_wait(5)
    bot.login()
    bot.search_jobs(config.search_string)
    ids = []
    ids.extend(bot.get_job_ids())
    while bot.next_page() and len(ids) < config.max_jobs:
        ids.extend(bot.get_job_ids())

    for job_id in ids:
        already_applied = is_id_in_csv(job_id)
        if not already_applied:
            bot.apply(job_id)

if __name__ == '__main__':
    main()

