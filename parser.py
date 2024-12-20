from bs4 import BeautifulSoup
import pymongo
import re


def parser(html):
    soup = BeautifulSoup(html, 'html.parser')
    faculty_list = []

    # h2 tags is where the faculty information is located
    faculty_sections = soup.find_all('h2')

    for section in faculty_sections:
        faculty = {}

        # Get name from h2 tag
        faculty['name'] = section.text.strip()

        # Get all text up to the next h2 tag or hr tag
        current_element = section
        text_content = []

        while current_element:
            next_element = current_element.next_sibling
            if next_element is None:
                break
            if next_element.name == 'h2' or next_element.name == 'hr':
                break
            if isinstance(next_element, str):
                text_content.append(next_element.strip())
            else:
                text_content.append(next_element.get_text().strip())
            current_element = next_element

        # Join all text content
        text_block = ' '.join(text_content)

        # Extract title
        title_match = re.search(r'Title:?\s*([^\n]*?)(?=Office:|$)', text_block)
        if title_match:
            faculty['title'] = title_match.group(1).strip()

        # Extract office
        office_match = re.search(r'Office:?\s*([^\n]*?)(?=Phone:|$)', text_block)
        if office_match:
            faculty['office'] = office_match.group(1).strip()

        # Extract phone
        phone_match = re.search(r'Phone:?\s*([^\n]*?)(?=Email:|$)', text_block)
        if phone_match:
            faculty['phone'] = phone_match.group(1).strip()

        # Extract email
        email_match = re.search(r'Email:?\s*([^\n]*?)(?=Web:|$)', text_block)
        if email_match:
            email = email_match.group(1).strip()
            email = email.replace('<', '').replace('>', '')
            faculty['email'] = email.strip()

        # Extract website
        web_match = re.search(r'Web:?\s*([^\n]*)', text_block)
        if web_match:
            website = web_match.group(1).strip()
            faculty['website'] = website.strip()

        # Only add faculty if we have valid name and title
        if faculty['name'] and 'title' in faculty and faculty['title']:
            # Clean up any remaining whitespace or newlines in values
            for key in faculty:
                if isinstance(faculty[key], str):
                    faculty[key] = ' '.join(faculty[key].split())
            faculty_list.append(faculty)

    return faculty_list


def main():
    # Connect to MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["cs_faculty"]

    # Find the target page (faculty page) from the pages collection
    faculty_page = db.pages.find_one({"is_target": True})

    if not faculty_page:
        print("Faculty page not found in database!")
        return

    # Extract faculty information from the HTML
    faculty_list = parser(faculty_page['html'])

    # Store faculty information in the professors collection
    if faculty_list:
        # Drop existing collection to avoid duplicates
        db.professors.drop()

        # Insert all faculty members
        db.professors.insert_many(faculty_list)
        print(f"Successfully stored information for {len(faculty_list)} professors")

        # Print stored information for verification
        print("\nStored faculty information:")
        for prof in db.professors.find():
            print(f"\nName: {prof.get('name')}")
            print(f"Title: {prof.get('title')}")
            print(f"Office: {prof.get('office')}")
            print(f"Phone: {prof.get('phone')}")
            print(f"Email: {prof.get('email')}")
            print(f"Website: {prof.get('website')}")
            print("-" * 50)
    else:
        print("No faculty information found!")


if __name__ == "__main__":
    main()
