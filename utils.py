import base64
import re

# Encode an image into base64
def encode_image(image_path : str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    
# Function to sort slide list
def extract_number(filename : str):
    match = re.search(r'slide_(\d+)', filename)
    return int(match.group(1)) if match else 0

# Function to sort audio list
def extract_speech(filename : str):
    match = re.search(r'speech_(\d+)', filename)
    return int(match.group(1)) if match else 0

# Prompt of generate content from slide
def gen_content_system_prompt(number_slides :int, slide_id : int):
    system_prompt = f"""
    Tôi đang thực hiện một dự án có khả năng chuyển slide thành một bài giảng dưới dạng video. Do đó, tôi muốn rằng khi tôi cung cấp cho bạn một hình ảnh của một slide và thông tin history chứa văn bản tóm tắt của các slide trước đó, bạn phải viết cho tôi script về slide đó. Yêu cầu về script:
    - Có tổng cộng {number_slides} slides và ban đang ở slide thứ {slide_id}
    - Bạn không được bịa ra các thông tin bằng cách suy đoán từ nội dung của slide, nội dung bạn nói ra phải có thật và được kiểm chứng
    - Giới thiệu nội dung mở đầu phải phù hợp với toàn bộ nội dung của slide. Từ slide thứ 2 trở đi, không cần giới thiệu các thông tin về công ty cho mỗi slide.
    - Bạn hãy dẫn dắt người dùng đi vào nội dung chính bằng cách đi từ khái quát đến cụ thể, thêm vào những ví dụ thực tiễn nếu cần thiết để người dùng dễ hình dung. Lưu ý các ví dụ này phải có thật vì người dùng sẽ yêu cầu cung cấp các đường dẫn tới ví dụ này
    - Trình bày các phần cần mạch lạc và liên kết chặt chẽ với nhau.
    - Ngôn ngữ dễ hiểu, viết bằng tiếng việt, đối với các thuật ngữ, khái niệm tiếng anh cần giữ nguyên.
    - Có thể mở rộng câu chuyện bằng cách giới thiệu các khái niệm, định nghĩa cần thiết liên quan. Tuyệt đối không được bịa ra thêm hoặc suy đoán nội dung các slide phía sau.
    - Nên nhớ đây là một bài giảng, cần đề cao việc truyền đạt kiến thức cho người học. Không nên chỉ có các nội dung cứng nhắc để nói về các khái niệm. Đôi khi cần đưa vào các ví dụ thực tế, sinh động và hài hước để dễ hiểu và giúp học viên dễ nhớ.
    - Không trình bày lan man làm cho bài giảng bị dài mà không truyền đạt tốt kiến thức cần thiết.
    - [QUAN TRỌNG + BẮT BUỘC] Tuyệt đối không được bịa ra thêm hoặc suy đoán nội dung các slide phía sau.
    - Ở câu cuối cùng không được giới thiệu nội dung của những slide tiếp theo
    - Với slide đầu tiên, đây chỉ là slide giới thiệu cơ bản, bạn chỉ cần giới thiệu tên và mục đích của buổi thuyết trình, không cần diễn giải thêm
    [BONUS]:
    Một content slide tốt thì bao gồm có
    - Overview về slide 
    - Nói kỹ về khái niệm chính trong slide và đưa ra các vấn đề liên quan
    - Với những khái niệm/thông tin mà bạn nghĩ người nghe sẽ khó hiểu hãy đưa ra các ví dụ minh họa cụ thể hoặc các thông tin có thật và có liên quan và bạn phải giải thích rõ các ví dụ, thông tin này nhưng không được lạm dụng việc này 
    - Liên kết với những gì đã được trình bày trong history

    =====
    Sau khi tạo script cho slide đó, bạn cần làm thêm 1 việc nữa là summarize lại nội dung đã trình bày một cách ngắn gọn. Viết thành các ý nhỏ, thay vì viết thành từng đoạn lớn. Thông tin đã summarize này sẽ được dùng để cung cấp thông tin cho lần tạo script của slide sau để tránh bị trùng lặp nội dung.
    Bên cạnh đó, dựa vào nội dung hãy tạo 1 title cho slide đó 
    Cuối cùng, trả về json với 3 keys là "title","answer" và "summary".
    
    Ví dụ : 
    
    Input : 
    Đây là slide đầu tiên, bạn hãy nhớ chào người nghe
    Ảnh của slide hiện tại như sau, hãy viết script cho nó.
    Output : 
    title : Giới thiệu về Twitter
    answer: Chào mừng các bạn đến với phần trình bày về Twitter - một mạng xã hội mới để trao đổi thông tin
    summary: [
        Giới thiệu về Twitter
    ]
    
    Input : 
    Với thông tin các slide trước đó như sau:
    Slide 1 : 
    [
        Twitter là giải pháp toàn diện cho giới trẻ.,
        Công cụ này giúp giao tiếp và truyền tải thông tin chính xác giữa các ngôn ngữ.,
        Twitter.io tích hợp nhiều tính năng ưu việt như facebook, instagram.,
        Hỗ trợ dịch thuật đa ngôn ngữ cho nhiều loại nội dung khác nhau.,
        Tích hợp các công cụ hỗ trợ như kiểm tra ngữ pháp, từ điển chuyên ngành, và khả năng tùy chỉnh.
    ]
    Lưu ý, hãy nhớ rằng đây không phải là slide đầu tiên, câu đầu tiên bạn không cần chảo mà chỉ cần giới thiệu về nội dung của slide này
    Đây là title của slide trước đó, nếu title của slide này có nội dung trùng với title của slide trước, hãy tiếp tục mà không cần giới thiệu lại, còn nếu không trùng nhau nhưng có liên quan thì bạn hãy dẫn dắt câu chuyện sang slide hiện tại sao cho người nghe có thể dễ hình dung: Các giải pháp
     =====
        Ảnh của slide hiện tại như sau, hãy viết script cho nó.
    Output : 
    "title" : Tính năng của Twitter
    "answer": "Bên cạnh các giải pháp đã được đề cập, trong phần này, chúng ta sẽ cùng nhau khám phá các tính năng nổi bật của Twitter. Đầu tiên, chúng ta sẽ xem xét tính năng chat với bạn bè. Tính năng này hỗ trợ chat với nhiều bạn bè cùng lúc, từ người quen đến người lạ ,ví dụ bạn có thể chat với một người ở Châu Phi, mặc dù khoảng cách rất xa nhưng không có gì ảnh hưởng. Tiếp theo, chúng ta sẽ tìm hiểu về tính năng upload hình ảnh, cho phép dịch hình ảnh về ngôn ngữ của bạn.Ví dụ như những hình ảnh nước ngoài thì với bạn nó sẽ được dịch sang đúng ngôn ngữ của bạn. Bên cạnh đó, chúng ta sẽ xem xét tính năng dịch âm thanh, giúp chuyển đổi tệp âm thanh thành văn bản một cách chính xác và nhanh chóng.",
    "summary": [
        "Demo các tính năng của Twiter.",
        "Tính năng chat với bạn bè, người lạ.",
        "Tính năng upload hình ảnh.",
        "Tính năng dịch âm thanh chuyển đổi tệp âm thanh thành văn bản."
    ]
    
     Input : 
    Với thông tin các slide trước đó như sau:
    Slide 1 : 
    [
        Doctranslate.io là giải pháp dịch thuật toàn diện cho doanh nghiệp.,
        Công cụ này giúp giao tiếp và truyền tải thông tin chính xác giữa các ngôn ngữ.,
        Doctranslate.io tích hợp nhiều tính năng ưu việt như dịch thuật chính xác, nhanh chóng và bảo mật.,
        Hỗ trợ dịch thuật đa ngôn ngữ cho nhiều loại nội dung khác nhau.,
        Tích hợp các công cụ hỗ trợ như kiểm tra ngữ pháp, từ điển chuyên ngành, và khả năng tùy chỉnh.
    ]
    Slide 2 : 
    [
        Khách hàng thường xuyên sử dụng Doctranslate và thấy công cụ rất hữu ích.,
        Chất lượng dịch thuật cao, có khả năng tùy biến tone giọng và lĩnh vực dịch.,
        Có thể dịch văn bản trong hình ảnh.,
        Đội ngũ hỗ trợ nhiệt tình và chuyên nghiệp.,
        Khách hàng rất hài lòng với dịch vụ của Doctranslate.
    ]
    Lưu ý, hãy nhớ rằng đây không phải là slide đầu tiên, câu đầu tiên bạn không cần chào mà chỉ cần giới thiệu về nội dung của slide này
    Đây là title của slide trước đó, nếu title của slide này có nội dung trùng với title của slide trước, hãy tiếp tục mà không cần giới thiệu lại, còn nếu không trùng nhau nhưng có liên quan thì bạn hãy dẫn dắt câu chuyện sang slide hiện tại sao cho thật mượt mà:Các gói dịch vụ
     =====
        Ảnh của slide hiện tại như sau, hãy viết script cho nó.
    Output : 
    title : Các gói dịch vụ
    answer: Có ba gói dịch vụ chính mà Twitter cung cấp.Mỗi gói dịch vụ đều được thiết kế để đáp ứng các nhu cầu dịch thuật khác nhau của doanh nghiệp, từ nhu cầu dịch tài liệu lớn đến các yêu cầu linh hoạt và đặc thù hơn. \n\nĐầu tiên, chúng ta sẽ nói về Gói 25.000 Credits. Gói này cung cấp 25.000 credits với giá 1.000 USD. Đây là lựa chọn lý tưởng cho các doanh nghiệp có nhu cầu dịch tài liệu với số lượng lớn.Để dễ hình dung tôi sẽ lấy ví dụ như các công ty liên quan đến in ấn, xuất bản sách. Với gói này, doanh nghiệp có thể dễ dàng quản lý và dịch thuật một lượng lớn tài liệu mà không phải lo lắng về chi phí phát sinh.\n\nTiếp theo là Gói 150.000 Credits. Gói này cung cấp 150.000 credits với giá 5.000 USD. Đây là lựa chọn hoàn hảo cho các doanh nghiệp thường xuyên dịch tài liệu với số lượng lớn. Gói này không chỉ giúp tiết kiệm chi phí mà còn mang lại sự thoải mái và tiện lợi trong quá trình dịch thuật.\n\nTiếp theo, chúng ta có Gói Tùy Chỉnh. Gói này cho phép doanh nghiệp lựa chọn số lượng credits theo nhu cầu cụ thể của họ. Giá của gói này sẽ được tính toán dựa trên số lượng credits yêu cầu. Đây là lựa chọn linh hoạt nhất, phù hợp cho các doanh nghiệp có nhu cầu dịch thuật đặc thù và không cố định.Lấy ví dụ là một doanh nghiệp nhỏ làm việc theo đơn đặt hàng, bạn có thể dễ dàng tùy chỉnh theo gói này.\n\nĐể đăng ký các gói dịch vụ này, các bạn có thể truy cập vào link: https://doctranslate.io/credit-recharge. Hãy lựa chọn gói dịch vụ phù hợp nhất với nhu cầu của doanh nghiệp bạn để tận hưởng những lợi ích mà Doctranslate.io mang lại.,
    summary: [
        Gói 25.000 Credits: 25.000 credits, giá 1.000 USD, dành cho doanh nghiệp có nhu cầu dịch tài liệu lớn.,
        Gói 150.000 Credits: 150.000 credits, giá 5.000 USD, dành cho doanh nghiệp thường xuyên dịch tài liệu lớn.,
        Gói Tùy Chỉnh: Số lượng credits và giá theo nhu cầu doanh nghiệp, phù hợp với nhu cầu dịch thuật linh hoạt.
    ]
    """
    return system_prompt

# Prompt of review content
def review_content_prompt(content_str : str):
    system_prompt = f"""
    Bạn là một nhà văn có khả năng viết lại nội dung của một bài thuyết trình thô sơ thành một bài thuyết trình hoàn chỉnh có thể khiến thu hút sự chú ý của người nghe và làm cho người nghe dễ hiểu
        Với những đoạn văn tách biệt nhau, bạn có thể đọc và hiểu nội dung của chúng rồi viết lại thành một bài thuyết trình với những câu từ phong phú, ví dụ minh họa, liên kết tới những kiến thức bên ngoài 
        Ở đầu mỗi đoạn văn, bạn thường dùng những câu hook để thu hút sự chú ý của người nghe, những câu hook này sẽ giới thiệu nội dung bạn sắp trình bày bằng cách đưa ra những thông tin và vấn đề liên quan, phải liên kết mạch lạc với slide phía trước và cấu trúc của các câu hook này không bị lặp lại giống nhau
        Với những thuật ngữ chuyên ngành khó tiếp cận với mọi người, bạn có thể diễn giải nó lại sao cho bất cứ ai cũng có thể hiểu được
        Về phần nội dung, bạn có thể sửa lại câu từ, cách truyền đạt để bài văn không bị khô khan và khó hiểu. 
        Với những thuật ngữ mà bạn nghĩ người nghe sẽ không hiểu, bạn sẽ thêm vào các ví dụ cụ thể và giải thích ví dụ đó 
        """
    user_prompt = f"""
        Đây là nội dung của bài thuyết trình của tôi  : 
        {content_str}
        Với nội dung của bài thuyết trình mà tôi cung cấp, tôi muốn bạn hãy viết lại nội dung của mỗi slide sao cho : 
        + Nội dung của các slide phải được liên kết mạch lạc và chặt chẽ với nhau bằng các câu ở đầu mỗi nội dung của slide, đặc biệt các câu đầu mỗi nội dung của các slide không được lặp lại cấu trúc
        + Bên cạnh nội dung chính của slide, hãy viết thêm các nội dung mà bạn nghĩ có thể giúp bài thuyết trình trở nên thú vị hơn
        + Hãy thay thế các danh từ riêng như tên công ty, sản phẩm, nền tảng,... bằng các đại từ như : công cụ này, sản phẩm này, công ty này, nền tảng này,...khi danh từ riêng đó đã được đề cập ở câu trước nhưng không được lạm dụng việc này
        + Tôi muốn câu hook dẫn vào slide phải thật thú vị, phải làm cho người nghe có thể chú ý tới
        Ví dụ về câu hook dẫn vào một slide nói về mạng xã hội : Khoảng cách thế hệ không thể ngăn cản được bước tiến của công nghệ, đối với giới trẻ hiện nay chúng ta cần một mạng xã hội mới để đáp ứng được nhu cầu của chúng và đó là cách mà Twitter ra đời
        Lưu ý : Số slide bạn trả về phải bằng đúng số slide input của tôi
        Cuối cùng, trả về nội dung của từng slide mới mà bạn đã chỉnh sửa thành file json với key là slide + số thứ tự 
        """
    return system_prompt, user_prompt