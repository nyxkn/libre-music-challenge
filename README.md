# Libre Music Challenge

## Run

``` sh
pipenv install
pipenv shell
python server.py
```

## Development setup

Install CSS frameworks

``` sh
npm install tailwindcss
npm install daisyui
```

Run CSS compilation

``` sh
npx tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --watch
```
