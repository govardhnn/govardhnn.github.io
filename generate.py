import yaml
from jinja2 import Environment, FileSystemLoader

# Load the data
with open('data.yaml', 'r') as file:
    data = yaml.safe_load(file)

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('template.html')

# Render the template
output = template.render(data)

# Write the output to a file
with open('index.html', 'w') as file:
    file.write(output)

print("Website generated successfully!")