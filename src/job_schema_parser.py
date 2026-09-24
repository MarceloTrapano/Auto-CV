import os


class JobSchemaParser:
    def __init__(self, filename: str | None = None, sep: str = "## "):
        self.filename = filename
        self.sep = sep
        self.ABOUT = "About\n"
        self.PERSON = "Person\n"
        self.EDUCATION = "Edu-"
        self.WORK_EXPERIENCE = "Work-"
        self.PROJECTS = "Proj-"
        self.ACTIVITIES = "Act-"
        self.SKILLS = "Skills\n"
        self.HOBBIES = "Hobbies\n"

    def set_filename(self, filename: str):
        self.filename = filename

    def _parse_keys(self, section, keys, sep: str = "\n"):
        informations: list[str] = section.split(sep)[1:]
        result = {}

        current_key = None
        for information in informations:

            new_key = None
            for key in keys:
                if information.startswith(key):
                    new_key = key
                    break

            if new_key:
                current_key = new_key
                result[current_key[:-1]] = information.split(key)[1].strip()
            elif current_key is not None and information.strip() != "":
                result[current_key[:-1]] += "\n" + information.strip()

        return result

    def _parse_title(self, section) -> str:
        return section.split("\n")[0]

    def parse(self):
        with open(self.filename, "r", encoding="utf-8") as file:
            text = file.read()

        sections: list[str] = text.split(self.sep)[1:]

        result = {}
        result["Activities"] = {}
        result["Education"] = {}
        result["Projects"] = {}
        result["Work_experience"] = {}
        for section in sections:
            if section.startswith(self.ABOUT):
                result["About"] = section.split(
                    "---")[0].split(self.ABOUT)[1]
            elif section.startswith(self.PERSON):
                result["Person"] = self._parse_keys(section, keys=[
                    "name:",
                    "email:",
                    "phone:",
                    "github:",
                    "linkedin:"
                ])
            elif section.startswith(self.EDUCATION):
                result["Education"][self._parse_title(
                    section)] = self._parse_keys(section, keys=[
                        "school:",
                        "degree:",
                        "course:",
                        "start:",
                        "end:",
                        "description:",
                    ])
            elif section.startswith(self.WORK_EXPERIENCE):
                result["Work_experience"][self._parse_title(
                    section)] = self._parse_keys(section, keys=[
                        "company:",
                        "position:",
                        "start:",
                        "end:",
                        "description:",
                    ])
            elif section.startswith(self.PROJECTS):
                result["Projects"][self._parse_title(
                    section)] = self._parse_keys(section, keys=[
                        "name:",
                        "stack:",
                        "repo:",
                        "description:",
                    ])
            elif section.startswith(self.ACTIVITIES):
                result["Activities"][self._parse_title(
                    section)] = self._parse_keys(section, keys=[
                        "organization:",
                        "role:",
                        "start:",
                        "end:",
                        "description:"
                    ])
            elif section.startswith(self.SKILLS):
                result["Skills"] = section.split(
                    "---")[0].split(self.SKILLS)[1]
            elif section.startswith(self.HOBBIES):
                result["Hobbies"] = section.split(
                    "---")[0].split(self.HOBBIES)[1]
            else:
                raise ValueError(f"Cannot parse this section: {section}")
        return result


if __name__ == "__main__":
    filename = os.path.abspath("job_schema.md")
    parser = JobSchemaParser(filename)

    print(parser.parse())
