import { useEffect, useMemo, useState } from 'react'

const NOME_CLASSE = ['Baixo', 'Médio', 'Alto']
const NOME_SINAL = {
  urgencia: 'Urgência',
  transferencia: 'Transferência',
  premio: 'Prêmio',
  falsa_identidade: 'Falsa identidade',
}
const POR_PAGINA = 20

const pct = (v) => `${(v * 100).toFixed(1)}%`

function Risco({ valor }) {
  return <span className={`risco r${valor}`}>{NOME_CLASSE[valor]}</span>
}

function Resultado({ pred, real }) {
  if (pred == null) return <span className="vazio">—</span>
  const ok = pred === real
  return (
    <span className="resultado">
      <Risco valor={pred} />
      <span className={ok ? 'ok' : 'erro'}>{ok ? '✓ acertou' : '✗ errou'}</span>
    </span>
  )
}

function SinaisMini({ sinais, ordem }) {
  return (
    <div className="mini">
      {ordem.map((s) => (
        <div key={s} className="mini-linha" title={`${NOME_SINAL[s]}: ${sinais[s]}`}>
          <span className="mini-rot">{NOME_SINAL[s].slice(0, 5)}</span>
          <span className="mini-trilho"><span className="mini-barra" style={{ width: pct(sinais[s]) }} /></span>
          <span className="mini-val">{sinais[s].toFixed(2)}</span>
        </div>
      ))}
    </div>
  )
}

function BarrasProb({ probs, real }) {
  return (
    <div className="probs">
      {probs.map((p, k) => (
        <div key={k} className="prob-linha">
          <span className="prob-rot">{NOME_CLASSE[k]}{k === real ? ' (real)' : ''}</span>
          <span className="prob-trilho"><span className={`prob-barra r${k}`} style={{ width: pct(p) }} /></span>
          <span className="prob-val">{pct(p)}</span>
        </div>
      ))}
    </div>
  )
}

function Detalhe({ linha, dados, aoFechar }) {
  const { sinais: ordem, classico } = dados
  const x = ordem.map((s) => linha.sinais[s])
  const scores = classico.coef.map((w, k) => classico.intercepto[k] + w.reduce((acc, wi, i) => acc + wi * x[i], 0))

  return (
    <aside className="detalhe">
      <div className="detalhe-topo">
        <h2>Mensagem #{linha.id}</h2>
        <button className="fechar" onClick={aoFechar} aria-label="Fechar detalhe">✕</button>
      </div>
      <p className="balao">“{linha.texto}”</p>
      <p className="meta">Risco real: <Risco valor={linha.risco_real} /> · conjunto de {linha.conjunto}</p>

      <h3>1. Sinais extraídos → ângulos nos qubits</h3>
      <table className="calc">
        <thead><tr><th>Sinal</th><th>Valor x</th><th>Ângulo θ = π·x</th></tr></thead>
        <tbody>
          {ordem.map((s, i) => (
            <tr key={s}>
              <td>q{i} · {NOME_SINAL[s]}</td>
              <td>{x[i].toFixed(2)}</td>
              <td>{(Math.PI * x[i]).toFixed(3)} rad</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>2. Baseline clássico (regressão logística)</h3>
      <p className="explica">Para cada classe: pontuação = b + Σ wᵢ·xᵢ. Depois, softmax transforma as pontuações em probabilidades.</p>
      <table className="calc">
        <thead>
          <tr><th>Classe</th><th>b</th>{ordem.map((s) => <th key={s}>w·{NOME_SINAL[s].slice(0, 5)}</th>)}<th>Pontuação</th></tr>
        </thead>
        <tbody>
          {classico.coef.map((w, k) => (
            <tr key={k}>
              <td>{NOME_CLASSE[k]}</td>
              <td>{classico.intercepto[k].toFixed(2)}</td>
              {w.map((wi, i) => <td key={i}>{(wi * x[i]).toFixed(2)}</td>)}
              <td><b>{scores[k].toFixed(2)}</b></td>
            </tr>
          ))}
        </tbody>
      </table>
      <BarrasProb probs={linha.classico.probs} real={linha.risco_real} />
      <p className="veredito">Resultado: <Resultado pred={linha.classico.pred} real={linha.risco_real} /></p>

      <h3>3. VQC quântico (simulador)</h3>
      {linha.vqc ? (
        <>
          <p className="explica">
            Os ângulos entram no feature map, o ansatz aplica {dados.vqc.parametros} parâmetros θ treinados e a medição
            dos {dados.vqc.qubits} qubits gera a probabilidade de cada classe.
          </p>
          <BarrasProb probs={linha.vqc.probs} real={linha.risco_real} />
          <p className="veredito">Resultado: <Resultado pred={linha.vqc.pred} real={linha.risco_real} /></p>
        </>
      ) : (
        <p className="explica">VQC ainda não treinado. Rode <code>python src/treinar.py</code> para gerar este cálculo.</p>
      )}
    </aside>
  )
}

export default function App() {
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState(null)
  const [busca, setBusca] = useState('')
  const [filtroReal, setFiltroReal] = useState('todos')
  const [conjunto, setConjunto] = useState('teste')
  const [soErros, setSoErros] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [selecionada, setSelecionada] = useState(null)

  useEffect(() => {
    fetch('/predicoes.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setDados)
      .catch((e) => setErro(e.message))
  }, [])

  const filtradas = useMemo(() => {
    if (!dados) return []
    const termo = busca.trim().toLowerCase()
    return dados.linhas.filter((l) => {
      if (conjunto !== 'todos' && l.conjunto !== conjunto) return false
      if (filtroReal !== 'todos' && l.risco_real !== Number(filtroReal)) return false
      if (termo && !l.texto.toLowerCase().includes(termo)) return false
      if (soErros) {
        const errouCls = l.classico.pred !== l.risco_real
        const errouVqc = l.vqc && l.vqc.pred !== l.risco_real
        if (!errouCls && !errouVqc) return false
      }
      return true
    })
  }, [dados, busca, filtroReal, conjunto, soErros])

  useEffect(() => setPagina(0), [busca, filtroReal, conjunto, soErros])

  if (erro) {
    return (
      <main className="app">
        <p className="aviso">
          Não consegui ler <code>predicoes.json</code> ({erro}). Rode <code>python src/treinar.py</code> na raiz do projeto e recarregue.
        </p>
      </main>
    )
  }
  if (!dados) return <main className="app"><p className="aviso">Carregando resultados…</p></main>

  const m = dados.metricas
  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA))
  const visiveis = filtradas.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA)
  const linhaSel = selecionada != null ? dados.linhas[selecionada] : null

  return (
    <main className="app">
      <header className="topo">
        <div>
          <p className="eyebrow">QTRUST · MOTOR DE RISCO</p>
          <h1>Resultados por mensagem</h1>
        </div>
        <p className="gerado">Gerado em {new Date(dados.gerado_em).toLocaleString('pt-BR')}</p>
      </header>

      <section className="cartoes">
        <div className="cartao"><span className="c-rot">Mensagens</span><span className="c-val">{dados.linhas.length}</span><span className="c-sub">{dados.linhas.filter((l) => l.conjunto === 'teste').length} no teste</span></div>
        <div className="cartao"><span className="c-rot">Clássico · acurácia no teste</span><span className="c-val">{pct(m.classico.acuracia)}</span><span className="c-sub">F1 risco alto {pct(m.classico.f1_alto)}</span></div>
        <div className="cartao quantico">
          <span className="c-rot">VQC · acurácia no teste</span>
          {m.vqc_simulador ? (
            <>
              <span className="c-val">{pct(m.vqc_simulador.acuracia)}</span>
              <span className="c-sub">F1 risco alto {pct(m.vqc_simulador.f1_alto)} · {dados.vqc.iteracoes} iterações</span>
            </>
          ) : (
            <><span className="c-val">—</span><span className="c-sub">ainda não treinado</span></>
          )}
        </div>
      </section>

      <section className="filtros">
        <input type="search" placeholder="Buscar no texto da mensagem…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar mensagem" />
        <label>Conjunto
          <select value={conjunto} onChange={(e) => setConjunto(e.target.value)}>
            <option value="teste">Teste</option>
            <option value="treino">Treino</option>
            <option value="todos">Todos</option>
          </select>
        </label>
        <label>Risco real
          <select value={filtroReal} onChange={(e) => setFiltroReal(e.target.value)}>
            <option value="todos">Todos</option>
            <option value="0">Baixo</option>
            <option value="1">Médio</option>
            <option value="2">Alto</option>
          </select>
        </label>
        <label className="check"><input type="checkbox" checked={soErros} onChange={(e) => setSoErros(e.target.checked)} /> Só onde algum modelo errou</label>
        <span className="contagem">{filtradas.length} mensagens</span>
      </section>

      <div className={`corpo ${linhaSel ? 'com-detalhe' : ''}`}>
        <div className="tabela-wrap">
          <table className="tabela">
            <thead>
              <tr><th>#</th><th>Mensagem</th><th>Sinais</th><th>Real</th><th>Clássico</th><th>VQC</th></tr>
            </thead>
            <tbody>
              {visiveis.map((l) => (
                <tr key={l.id} className={selecionada === l.id ? 'sel' : ''} onClick={() => setSelecionada(l.id)} tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && setSelecionada(l.id)}>
                  <td className="num">{l.id}</td>
                  <td className="texto">{l.texto}</td>
                  <td><SinaisMini sinais={l.sinais} ordem={dados.sinais} /></td>
                  <td><Risco valor={l.risco_real} /></td>
                  <td><Resultado pred={l.classico.pred} real={l.risco_real} /></td>
                  <td><Resultado pred={l.vqc?.pred} real={l.risco_real} /></td>
                </tr>
              ))}
              {visiveis.length === 0 && <tr><td colSpan={6} className="vazio">Nenhuma mensagem com esses filtros.</td></tr>}
            </tbody>
          </table>
          <div className="paginacao">
            <button disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>← Anterior</button>
            <span>Página {pagina + 1} de {totalPaginas}</span>
            <button disabled={pagina >= totalPaginas - 1} onClick={() => setPagina((p) => p + 1)}>Próxima →</button>
          </div>
        </div>
        {linhaSel && <Detalhe linha={linhaSel} dados={dados} aoFechar={() => setSelecionada(null)} />}
      </div>
    </main>
  )
}
