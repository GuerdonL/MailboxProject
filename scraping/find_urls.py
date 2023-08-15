from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import bs4, csv

form_id = "city-state-input"
search_id = "searchLocations"
location_item_class = "list-item-location popover-trigger"
location_item_xpath_1 = "/html/body/div[2]/div/div[2]/div[3]/div[5]/div[2]/div[1]/div[1]/*"
location_item_xpath_2 = "/html/body/div[2]/div/div[2]/div[3]/div[5]/div[2]/div[1]/div[2]/*"
show_filters_xpath = "/html/body/div[2]/div/div[2]/div[3]/div[2]/div/div[4]/div[2]/p/a"
gen_mail_xpath = "/html/body/div[2]/div/div[2]/div[3]/div[3]/div[2]/div[1]/label[3]"
url = "https://tools.usps.com/find-location.htm"
browser = webdriver.Chrome()

failed_zips = set()
po_ids = set()

def zip_gen():
    # starting_zip_code = "00501"
    # ending_zip_code = "99950"
    # for zip in range(int(starting_zip_code),int(ending_zip_code)+1):
    #     yield "0"*(5-len(str(int(zip))))+str(int(zip))
    with open("/home/guerdon/MailboxProject/scraping/geo-data.csv", 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for line in reader:
            yield line[3]

def handle_search(form,search):
    result_box_1,result_box_2=[],[]
    #iterate through potential zip codes from generator
    for zip in zip_gen():
        #delete last search, search next zip
        form.send_keys("\b\b\b\b\b"+zip)
        #wait for search button to be clickable, then click
        WebDriverWait(browser,10).until(
            EC.element_to_be_clickable(search)
        ).click()
        #get a list of all results
        try:
            result_box_1 = WebDriverWait(browser,3).until(
                EC.presence_of_all_elements_located((By.XPATH,location_item_xpath_1))
            )
            result_box_2 = WebDriverWait(browser,3).until(
                EC.presence_of_all_elements_located((By.XPATH,location_item_xpath_2))
            )
            for po in result_box_1:
                po_ids.add(po.get_property('id'))
                print(po.get_property('id'))
            for po in result_box_2:
                po_ids.add(po.get_property('id'))
                print(po.get_property('id'))
        except:
            print("timeout on zip search")
            failed_zips.add(zip)
        finally:
            with open('/home/guerdon/MailboxProject/scraping/ids.csv', 'w') as f:
                writer = csv.writer(f)
                writer.writerows([po_ids])
            with open('/home/guerdon/MailboxProject/scraping/failed_zips.csv', 'w') as f:
                writer = csv.writer(f)
                writer.writerows([failed_zips])

browser.get(url)
try:
    #click to show filter list
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, show_filters_xpath))
    ).click()
except:
    print("timed out looking for element")
else:
    #grab and toggle the general mailing option once visible 
    #(this is inconsistent, the previous toggle doesn't always toggle filter visibility, IDK)
    WebDriverWait(browser,10).until(
        EC.element_to_be_clickable((By.XPATH, gen_mail_xpath))
    ).click()
    #start the zip code stuff!
    form = browser.find_element(By.ID, form_id)
    search = browser.find_element(By.ID, search_id)
    handle_search(form,search)
finally:
    browser.quit()
browser.quit()
