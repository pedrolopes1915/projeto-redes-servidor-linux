import os
from contextlib import asynccontextmanager
from html import escape

import psycopg
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

def conn():
	# Credenciais
	return psycopg.connect(
		host=os.environ["DB_HOST"],
		dbname=os.environ["DB_NAME"],
		user=os.environ["DB_USER"],
		password=os.environ["DB_PASS"],
		connect_timeout=5,
	)

@asynccontextmanager
async def lifespan(app):
	# Cria tabela
	with conn() as c:
		c.execute(
			"CREATE TABLE IF NOT EXISTS recados ("
			"id SERIAL PRIMARY KEY, autor TEXT NOT NULL, "
			"mensagem TEXT NOT NULL, criado_em TIMESTAMPTZ DEFAULT now())"
		)
	yield

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
def home():
	with conn() as c:
		rows = c.execute(
			"SELECT autor, mensagem, criado_em FROM recados "
			"ORDER BY id DESC LIMIT 20"
		).fetchall()
	itens = "".join(
		f"<li><b>{escape(a)}</b>: {escape(m)} <small>({t:%d/%m/%Y %H:%M})</small></li>"
		for a, m, t in rows
	)
	return (
		"<h1>Mural de Recados</h1>"
		'<form method="post" action="/recado">'
		'<input name="autor" placeholder="nome" required>'
		'<input name="mensagem" placeholder="Mensagem" required>'
		"<button>Enviar</button></form>"
		f"<ul>{itens}</ul>"
	)

@app.post("/recado")
def novo_recado(autor: str = Form(...), mensagem: str = Form(...)):
	with conn() as c:
		c.execute(
			"INSERT INTO recados (autor, mensagem) VALUES (%s, %s)",
			(autor[:50], mensagem[:200]),
		)
	return RedirectResponse("/", status_code=303)
