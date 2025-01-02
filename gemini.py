from PIL import Image, ImageEnhance
import json
import google.generativeai as genai
from io import BytesIO

# Function to sharpen the image
def sharpen_image(image_data):
    try:
        image = Image.open(BytesIO(image_data))
        
        # Apply sharpening filter
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)  # Adjust the factor to sharpen the image (2.0 is a moderate sharpen)
        
        # Save the image to a BytesIO object
        output = BytesIO()
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info): 
            image_format = 'PNG' # Use PNG for images with transparency 
        else: 
            image_format = image.format if image.format else 'JPEG'
        image.save(output, format=image_format)
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        print("Error in the sharpen image method",e)
        return"error"

# Gemini API Function
async def process_result_card(image_data, api_key):
    try:
        # Configure the API
        genai.configure(api_key=api_key)

        # Set up the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Load and prepare image
        image = Image.open(BytesIO(image_data))
        # Prepare the prompt
        prompt = """
            Extract all subject details from the results image and create a JSON object with the following structure:
            {
                "cgpa": [
                    {
                        "course_name": "NAME OF COURSE IN CAPITALS",
                        "course_code": "SUBJECT CODE",
                        "course_credit": 0, // Default to 0 if not specified
                        "grade": "GRADE"
                    }
                ],
                "semester": "Extracted it from the image, should be an intiger"
            }
            Return only the JSON object without any additional text or explanations.
            if relevant information is not present and if for some reason the semester is null or the cgpa field is incomplete 
            then return only {"message": "error"} 
        """

        # Generate response from the model
        response = model.generate_content([prompt, image])

        # Extract text from response
        response_text = response.text

        # Clean up the response text to ensure it's valid JSON
        response_text = response_text.replace('```json', '').replace('```', '').strip()

        # Parse the response to ensure valid JSON
        result = json.loads(response_text)

        # Format with proper indentation
        return result  # Return the JSON object as a dictionary

    except Exception as e:
        print("Error in the gemini api method",e)
        return "error"
