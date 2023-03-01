import re
from bs4 import BeautifulSoup

class radio_soup:
    def get_stream(input):
        ###Opens html file from https://www.hendrikjansen.nl/henk/streaming.html with some known radio streaming urls
        with open('.\\radio_zenders.hmtl') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
    
        ###Searches all mentions of the given input       
        name_mentions = soup.find_all(string=re.compile(input, re.IGNORECASE))
        
        urls = []
        is_mp3 = False
        
        ###filters mentions into usable urls
        for name_mention in name_mentions:        
            string = name_mention.strip()
            url = ''
            
            ###Check if the mention itself is the url
            if 'http' in string:
                url = string
            
            parent = name_mention.parent
            
            ###if is a then it already is an url
            if parent.name == 'a':
                url = parent.get('href')
            
            ###.mp3's are usefull, aac's maybe not (not in a web browser)
            if '.mp3' in url:
                urls.insert(0, url)
                is_mp3 = True
            elif '.aac' in url:
                urls += [url]
            
        return is_mp3, urls