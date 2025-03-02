from gpt import GPT

if __name__ == '__main__':
    pdf_path = "./data"
    agent = GPT()
    agent.process_pdf_folder(pdf_path)