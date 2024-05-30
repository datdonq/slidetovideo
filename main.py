import os
import glob
import shutil
import dotenv
from mutagen.mp3 import MP3
import moviepy.editor as mp
from openai import OpenAI
import json
import fitz
import time
from tqdm import tqdm

from utils import *

dotenv.load_dotenv()

class CutPdf:
    @staticmethod
    def split_pdf_to_slides(pdf_path :str,
                            output_folder :str,
                            *args,
                            **kwargs):
        
        # Kiểm tra và tạo thư mục "slides" nếu chưa tồn tại
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)
        
        # Mở file PDF
        pdf_document = fitz.open(pdf_path)
        
        # Duyệt qua từng trang và lưu từng trang vào file ảnh riêng biệt
        for page_num in range(len(pdf_document)):
            
            page = pdf_document.load_page(page_num)  # Load trang
            pix = page.get_pixmap()  # Chuyển trang thành ảnh
            
            # Tạo đường dẫn lưu ảnh
            output_path = os.path.join(output_folder, f"slide_{page_num + 1}.png")
            
            # Lưu ảnh
            pix.save(output_path)

        print(f"Đã lưu {len(pdf_document)} trang vào thư mục '{output_folder}'.")

class GenContent:
    
    def __init__(self, client, MODEL):
        self.client = client
        self.MODEL = MODEL
        
    def content_from_slide(self, slide_path :str, duration_time : float = None , *args, **kwargs):
        
        # Lấy ra các slides từ thư mục và sắp xếp đúng thứ tự
        list_slides = [os.path.join(slide_path, i) for i in os.listdir(slide_path)]
        list_slides = [i for i in list_slides if i.endswith(".png")]
        list_slides=sorted(list_slides, key=extract_number)
        
        # Tạo thư mục để lưu script của từng slide
        if os.path.exists("scripts"):
            shutil.rmtree("scripts")
        os.makedirs("scripts")
        
        # Tính tổng số lượng slide
        number_slides = len(list_slides)
        
        word_per_minute = 270
        if duration_time : 
            total_word = duration_time * word_per_minute - 30 * number_slides
            word_per_slide = total_word // number_slides
            print("Word_per_slide : ", word_per_slide)
        # Duyệt qua từng slide và sinh ra script cho nó
        for idx, img_path in tqdm(enumerate(list_slides)):
            if duration_time : 
                script = self.get_slide_script(MODEL = self.MODEL,
                                            client = client, 
                                            image_path = img_path, 
                                            slide_id = idx+1,
                                            number_slides = number_slides,
                                            word_per_slide = word_per_slide)
            else : 
                script = self.get_slide_script(MODEL = self.MODEL,
                                            client = client, 
                                            image_path = img_path, 
                                            slide_id = idx+1,
                                            number_slides = number_slides)
            script = json.loads(script)

            # Lấy tên file từ img_path và thay đổi phần mở rộng thành .json
            filename = os.path.basename(img_path)
            json_filename = os.path.splitext(filename)[0] + '.json'
            
            # Tạo đường dẫn lưu file JSON
            output_path = os.path.join("./scripts", json_filename)
            
            # Lưu script dưới dạng file JSON
            with open(output_path, 'w', encoding='utf-8') as json_file:
                json.dump(script, json_file, ensure_ascii=False, indent=4)
                
        # Lưu các key "answer" của các file json thành 1 file content.json
        scripts = glob.glob("./scripts" + "/*.json")
        scripts = sorted(scripts,key = extract_number)
        
        index = 1
        content = {}
        
        # Duyệt qua tất cả các file json trong thư mục
        for file_path in scripts:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            slide = "Slide " + str(index)
            content[slide] = data["answer"]
            index += 1
        content_str = json.dumps(content, ensure_ascii=False, indent=4)
        with open('content.json', 'w', encoding='utf-8') as json_file:
            json.dump(content, json_file, ensure_ascii=False, indent=4)
        print("Save content")
        
        batches_content = split_dict_into_batches(content, 3)
        return batches_content
            
    def get_slide_script(self,
                         MODEL,
                         client, 
                         image_path : str,
                         slide_id :int,
                         number_slides : int,
                         word_per_slide : float = None,
                         *args,
                         **kwargs):
        
        # Chuyển hình ảnh của sldie sang dạng base64
        base64_image = encode_image(image_path)
        
        # Lưu lại history của các slide trước
        history = ""
        for i in range(1, slide_id):
            history += f"Slide {i}: \n"
            with open(f"./scripts/slide_{i}.json", "r", encoding="utf-8") as f:
                summary = json.load(f)["summary"]
                for line in summary:
                    history += "- " + line + "\n"
                    
        # Title của slide trước đó 
        slide_before= slide_id-1
        if slide_before !=0 : 
            with open(f"./scripts/slide_{slide_before}.json", "r", encoding="utf-8") as f:
                    title = json.load(f)["title"]

        if word_per_slide : 
        # Nếu có history của các slide trước đó 
            if history:
                user_prompt = f"""
                Với thông tin các slide trước đó như sau:
                {history}
                Lưu ý, hãy nhớ rằng đây không phải là slide đầu tiên, câu đầu tiên bạn không cần chảo mà chỉ cần giới thiệu về nội dung của slide này
                Đây là title của slide trước đó : {title}
                Nếu slide này có title giống với title của slide trước thì câu đầu tiên trong phần "answer" bạn không cần giới thiệu nội dung của slide này, nếu không giống nhưng có liên quan bạn hãy dẫn dắt từ slide trước qua slide này sao cho hợp lý
                =====
                Ảnh của slide hiện tại như sau, hãy viết script cho nó.
                Script bạn viết phải khoảng {word_per_slide} từ cho mỗi slide, hãy cắt bớt nội dung hoặc thêm nội dung nếu cần thiết
                """
            else:
                user_prompt = f"""
                Đây là slide đầu tiên, bạn hãy nhớ chào người nghe
                Ảnh của slide hiện tại như sau, hãy viết script cho nó.
                Script bạn viết phải khoảng {word_per_slide} từ cho mỗi slide, hãy cắt bớt nội dung hoặc thêm nội dung nếu cần thiế
                """
        else:
            if history:
                user_prompt = f"""
                Với thông tin các slide trước đó như sau:
                {history}
                Lưu ý, hãy nhớ rằng đây không phải là slide đầu tiên, câu đầu tiên bạn không cần chảo mà chỉ cần giới thiệu về nội dung của slide này
                Đây là title của slide trước đó : {title}
                Nếu slide này có title giống với title của slide trước thì câu đầu tiên trong phần "answer" bạn không cần giới thiệu nội dung của slide này, nếu không giống nhưng có liên quan bạn hãy dẫn dắt từ slide trước qua slide này sao cho hợp lý
                =====
                Ảnh của slide hiện tại như sau, hãy viết script cho nó.
                """
            else:
                user_prompt = f"""
                Đây là slide đầu tiên, bạn hãy nhớ chào người nghe
                Ảnh của slide hiện tại như sau, hãy viết script cho nó.
                """

        # Lấy response từ openAI
        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": gen_content_system_prompt(number_slides = number_slides, slide_id = slide_id)},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"}
                    }
                ]}
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content        
    
class Review:
    
    def __init__(self, client, MODEL):
        self.client = client
        self.MODEL = MODEL
        
    def get_review(self, content : str, *args, **kwargs):
        
        # Review content với openAI
        final_content = self.review_script(MODEL = self.MODEL, 
                                           client = self.client, 
                                           content = content)
        
        # Đưa content thành dạng list
        final_content = json.loads(final_content)
        final_content_list = list(final_content.values())
        with open("final_content.json", 'a', encoding='utf-8') as json_file:
            json.dump(final_content, json_file, ensure_ascii=False, indent=4)
        print("Save final content !")
        return final_content_list

    def review_script(self,
                      MODEL,
                      client,
                      content : str,
                      *args,
                      **kwargs):
        
        system_prompt, user_prompt = review_content_prompt(content_str = content)

        # Lấy response trả về từ openAI
        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content
    
class Text2Speech:
    
    def __init__(self, client):
        self.client = client
        
    def gen_audio(self, content_list : list, audios_path : str, new_speed : float = None, *args, **kwargs):
        
        if new_speed : 
            if new_speed > 1.45 or new_speed < 1.1:
                new_speed = 1.35
        else : 
            new_speed = 1.35
        # Text to speech
        for idx, caption in enumerate(content_list):
            speech_file_path = audios_path + f"/speech_{idx}.mp3"
            response = client.audio.speech.create(
            model = "tts-1",
            voice = "nova",
            input = caption,
            speed = new_speed
            )
            response.stream_to_file(speech_file_path)
            
class Slide2Video:
    
    def __init__(self, generate_content, review_content, text2speech):
        
        self.generate_content = generate_content
        self.review_content = review_content
        self.text2speech = text2speech
        
    def merge(self, pdf_path :str, duration_time : float = None, *args, **kwargs):
        
        # Set up path
        slide_path = "./slides"
        audio_path = "./audios"
        
        # Cut pdf to slides
        CutPdf.split_pdf_to_slides(pdf_path = pdf_path, output_folder = slide_path)
        
        final_content = []
        batches_content = self.generate_content.content_from_slide(slide_path = slide_path, duration_time = duration_time)
        for i, batch in enumerate(batches_content):
            content_str = batch_to_string(batch)
            # Review Content
            content_reviewed = self.review_content.get_review(content = content_str)
            final_content += content_reviewed


        combined_string = ' '.join(s.strip() for s in final_content)
        # Đếm số chữ (số ký tự không phải là khoảng trắng)
        total_word = len(combined_string.split())
        print(total_word)
        
        # Tạo lại folder để lưu audio
        if os.path.exists(audio_path):
            shutil.rmtree(audio_path)
        os.makedirs(audio_path)
        
        # Control merge error
        while True : 
            try : 
                if duration_time :
                    new_speed = (total_word/270)*1.35/duration_time
                    print(new_speed)
                    # Generate audio from content
                    self.text2speech.gen_audio(content_list = final_content, audios_path = audio_path, new_speed = new_speed)
                else : 
                    self.text2speech.gen_audio(content_list = final_content, audios_path = audio_path)
                # Get slide list and audio list
                slide_list = glob.glob(slide_path + "/*.png")
                audio_list = glob.glob(audio_path + "/*.mp3")
                slide_list = sorted(slide_list, key=extract_number)
                audio_list = sorted(audio_list, key=extract_speech)
                
                # Create video clips
                video_clips = []
                
                # Start merge
                for image, audio in zip(slide_list, audio_list):
                    audio_du = MP3(audio)
                    duration = audio_du.info.length
                
                    img_clip = mp.ImageClip(image).set_duration(duration)
                    audio_clip = mp.AudioFileClip(audio).subclip(0, duration)
            
                    video_clip = img_clip.set_audio(audio_clip)
                    video_clips.append(video_clip)

                # Save video
                final_video = mp.concatenate_videoclips(video_clips)
                final_video.write_videofile("output_video.mp4", fps=24)
                
                break
            except :
                pass
        
if __name__ == "__main__":
    
    # Set up 
    SECRET_KEY = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=SECRET_KEY)
    MODEL = "gpt-4o"
    
    # Call function
    generate_content = GenContent(client, MODEL)
    review_content= Review(client, MODEL)
    text2speech = Text2Speech(client)
    slide2video = Slide2Video(
        generate_content = generate_content, 
        review_content = review_content, 
        text2speech = text2speech
    )
    
    # Start 
    slide2video.merge(pdf_path = "voice_your_slide_input_demo.pdf", duration_time= 4)
    
    