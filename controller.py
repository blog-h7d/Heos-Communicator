import quart

app = quart.Quart("HEOS Communication Server")
app.secret_key = "HeosCommunication_ChangeThisKeyForInstallation"


@app.route('/')
async def main():
    return f'Hello World'


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)