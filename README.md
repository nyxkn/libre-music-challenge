# Libre Music Challenge

## Run

``` sh
pipenv install
pipenv run flask --app server run
```

## Development setup

Install CSS frameworks

``` sh
npm install -D tailwindcss
npm install -D @tailwindcss/typography
npm install -D daisyui
```

Run CSS compilation

``` sh
npx tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --watch
```
