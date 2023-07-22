from flask import Flask, request, jsonify
import os
import subprocess
import docker

DOCKER_IMAGE_NAME = "gcc"

app = Flask(__name__)

def run_cpp_code(cpp_code, compiler='gcc'):
    # Map user's compiler choice to the corresponding Docker image
    compiler_images = {
        'gcc': 'gcc',
        'clang': 'clang',
        'mingw': 'keryi/mingw-gcc',  # Docker image for MinGW-w64
        'msvc': 'mcr.microsoft.com/windows/nanoserver',  # Docker image for MSVC
        # Add more compiler options and their corresponding Docker images here
    }

    # Check if the user's compiler choice is supported
    if compiler not in compiler_images:
        return {"error": f"Compiler '{compiler}' is not supported."}

    # Get the Docker image name for the chosen compiler
    docker_image = compiler_images[compiler]

    # For MSVC, use PowerShell command to execute the code
    if compiler == 'msvc':
        command = f'powershell -Command "cl /EHsc /Fotemp /Feapp temp.cpp && .\\app"'
    else:
        command = f'bash -c "g++ /app/temp.cpp -o /app/temp && /app/temp"'

    # Create a Docker client
    client = docker.from_env()

    # Write the C++ code to a temporary file
    with open('temp.cpp', 'w') as f:
        f.write(cpp_code)

    try:
        # Run the C++ code inside the chosen Docker container
        container = client.containers.run(
            docker_image,
            command=command,
            remove=True,
            volumes={
                f'{os.getcwd()}': {'bind': '/app', 'mode': 'rw'}
            },
            working_dir='/app',
            detach=False
        )

        # Get the output from the container
        output = container.decode('utf-8').strip()

        # Remove temporary C++ file
        os.remove('temp.cpp')
        if compiler == 'msvc':
            os.remove('app.exe')
        else:
            os.remove('temp')

        # Prepare the response with the output
        return {"output": output}
    except docker.errors.ContainerError as e:
        # If the container returns an error, capture the error message
        error_output = e.stderr.decode('utf-8').strip()
        return {"error": error_output}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout error. The code took too long to execute."}
    except Exception as e:
        return {"error": str(e)}

@app.route('/run_cpp_code', methods=['POST'])
def execute_cpp_code():
    data = request.get_json()
    cpp_code = data.get('cpp_code', '')

    result = run_cpp_code(cpp_code)

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
