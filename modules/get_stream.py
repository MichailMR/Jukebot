import yt_dlp

class new_dl():
    def get_audio_stream(url):
        ydl_opts = {"format":'bestaudio',"format_sort":'acodec',"quiet":True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ###Get all information about the youtube video
            info = ydl.extract_info(url, download=False)
            
            ###Iterate through all of the available formats
            for i,format in enumerate(info['formats']):
                print(format["audio_ext"])
                if format["audio_ext"] in ('none', 'm4a') :
                    continue
                    
                return {"url":format['url'], "title":info["title"]}