import re
from bs4 import BeautifulSoup

class radio_soup:
    def get_stream(input):
        ###Opens html file from https://www.hendrikjansen.nl/henk/streaming.html with some known radio streaming urls
        with open('..\\radio_zenders.hmtl') as fp:
            soup = BeautifulSoup(fp, 'html.parser')
    
        ###Searches all mentions of the given input       
        name_mentions = soup.find_all(string=re.compile(input, re.IGNORECASE))
        
        urls = []
        radio_names = []
        
        ###filters mentions into usable urls
        for name_mention in name_mentions:        
            string, parent = name_mention.strip(), name_mention.parent
            url, radio_name = '', ''
                
            ###Check if parent has url
            if parent.name == 'a' and not parent.get('href') == None:
                url, radio_name = parent.get('href'), parent.get_text().strip()
                
            elif 'http' in name_mention:
                url, radio_name = name_mention.strip(), ''
                
                ###Find good name
                for segment in name_mention.strip().split('/'):
                    if input.upper() in segment.upper():
                        radio_name = segment.split('.')[0]
            
            ###Remove ugly string fragments
            for segment in radio_name.split(' '):
                if segment == 'â€”':
                    radio_name = ' '.join(radio_name.split(' ')[1:])
            radio_name = radio_name.replace('\n', '').replace('—', '').lower().strip()
        
            ###only add if it is an usefull audio file stream
            if '.mp3' in url or '.aac' in url or '.m3u8' in url:
                urls += [url]
                string = 'â€”'
                radio_names += [radio_name]
            
        return dict(zip(["urls", "radio_names"], [urls, radio_names]))