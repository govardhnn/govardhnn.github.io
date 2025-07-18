import yaml
from jinja2 import Environment, FileSystemLoader
import os

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))

# All the webpages that need to be generated:
pages = ['index.html', 'calendar.html', 'blog.html', "cv.html"]

for page in pages:
    # Load the data
    with open('data.yaml', 'r') as file:
        data = yaml.safe_load(file)

    # Load the template
    template_path = os.path.join('templates', page)
    template = env.get_template(template_path)

    # Render the template
    output = template.render(data)

    # Write the output to a file
    with open(page, 'w') as file:
        file.write(output)

    print("INFO: Generated", page)

# Generate all the blogs
blog_templates = ['comp_arch.html']

for blog in blog_templates:
    # Load the data
    with open('data.yaml', 'r') as file:
        data = yaml.safe_load(file)

    # Load the template
    template_path = os.path.join('templates', 'blog', blog)
    template = env.get_template(template_path)

    # Render the template
    output = template.render(data)

    # Write the output to a file
    output_path = os.path.join('blog', blog)
    with open(output_path, 'w') as file:
        file.write(output)

    print("INFO: Generated", output_path)