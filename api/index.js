const express = require('express');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const axios = require('axios');
const nodemailer = require('nodemailer');
const crypto = require('crypto');

const app = express();
app.use(express.json({limit:'2mb'}));
app.use(express.static('public'));

const mailer = nodemailer.createTransport({
  host:'smtp.gmail.com', port:587, secure:false,
  auth:{user:process.env.SMTP_USER, pass:process.env.SMTP_PASS}
});

const pedidos = new Map();

// ⚠️ CAMBIA ESTOS IDs por los que saques de Printify
const VARIANTES = {
  't-shirt':{S:'', M:'', L:'', XL:'', XXL:''},
  'hoodie':{S:'', M:'', L:'', XL:'', XXL:''}
};

async function refinar(prompt){
  const {data} = await axios.post('https://api.openai.com/v1/chat/completions',{
    model:'gpt-4-turbo',
    messages:[{role:'system',content:'Eres diseñador textil. Convierte esta idea en prompt profesional para DALL·E: colores vivos, vectorial, fondo transparente, apto para camiseta. Devuelve solo el prompt.'},{role:'user',content:prompt}]
  },{headers:{Authorization:`Bearer ${process.env.OPENAI_API_KEY}`,'Content-Type':'application/json'}});
  return data.choices[0].message.content;
}

async function generar(prompt){
  const {data} = await axios.post('https://api.openai.com/v1/images/generations',{
    model:'dall-e-3', prompt, n:2, size:'1024x1024'
  },{headers:{Authorization:`Bearer ${process.env.OPENAI_API_KEY}`,'Content-Type':'application/json'}});
  return data.data.map(i=>i.url);
}

async function subir(url){
  const buf = (await axios.get(url,{responseType:'arraybuffer'})).data;
  const {data:u} = await axios.post('https://api.printify.com/v1/uploads.json',{},{headers:{Authorization:`Bearer ${process.env.PRINTIFY_API_KEY}`}});
  await axios.put(u.upload_url, buf,{headers:{Authorization:`Bearer ${process.env.PRINTIFY_API_KEY}`,'Content-Type':'image/png'}});
  return u.id;
}

async function orden(variantId, fileId, email, extId){
  const {data:shops} = await axios.get('https://api.printify.com/v1/shops.json',{headers:{Authorization:`Bearer ${process.env.PRINTIFY_API_KEY}`}});
  const shopId = shops[0].id;
  const {data:o} = await axios.post(`https://api.printify.com/v1/shops/${shopId}/orders.json`,{
    external_id:extId,
    line_items:[{variant_id:variantId, quantity:1, files:[{id:fileId, placement:{x:0.5,y:0.5,scale:1,angle:0}}]}],
    recipient:{name:'Cliente',email}
  },{headers:{Authorization:`Bearer ${process.env.PRINTIFY_API_KEY}`,'Content-Type':'application/json'}});
  return o.data.id;
}

app.get('/', (req,res) => res.sendFile(__dirname+'/public/index.html'));

app.get('/exito', (req,res) => {
  res.send(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Generando...</title><style>body{font-family:Arial;padding:2rem;text-align:center}img{max-width:300px;margin:10px;border:2px solid #ddd;border-radius:8px;cursor:pointer}img.seleccionada{border-color:#0066ff}button{padding:12px 24px;margin:5px;border:none;border-radius:5px;cursor:pointer}#confirmBtn{background:#0066ff;color:#fff}#regBtn{background:#f0f0f0;border:1px solid #ccc}.hidden{display:none}</style></head><body>
  <div id="load"><h2>⏳ Generando tu diseño único...</h2></div>
  <div id="content" class="hidden"><h2>🎨 Elige tu diseño</h2><div id="imgs"></div><button id="confirmBtn" class="hidden">✅ Confirmar diseño</button><button id="regBtn">🔄 Nuevas opciones</button><p id="msg"></p></div>
  <script>
    const params=new URLSearchParams(location.search),sid=params.get('session_id');
    if(!sid) document.body.innerHTML='<h2>Error: falta session_id</h2>';
    let token=null;
    async function cargar(){try{
      const r=await fetch('/api/generar-diseno',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid})});
      const d=await r.json(); token=d.token; mostrar(d.imagenes);
    }catch(e){document.getElementById('load').innerHTML='<h2>Error al generar</h2>'}}
    function mostrar(imgs){
      document.getElementById('load').classList.add('hidden');
      document.getElementById('content').classList.remove('hidden');
      const c=document.getElementById('imgs'); c.innerHTML='';
      imgs.forEach((u,i)=>{const img=document.createElement('img');img.src=u;img.onclick=()=>{document.querySelectorAll('#imgs img').forEach(x=>x.classList.remove('seleccionada'));img.classList.add('seleccionada');document.getElementById('confirmBtn').classList.remove('hidden');document.getElementById('confirmBtn').dataset.index=i};c.appendChild(img)});
      document.getElementById('confirmBtn').onclick=async function(){
        document.getElementById('msg').textContent='⏳ Confirmando...';
        const r=await fetch('/api/confirmar-diseno',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,indice:parseInt(this.dataset.index)})});
        const d=await r.json(); document.getElementById('msg').textContent=d.mensaje;
        document.getElementById('confirmBtn').classList.add('hidden'); document.getElementById('regBtn').classList.add('hidden');
      };
      document.getElementById('regBtn').onclick=async function(){
        document.getElementById('msg').textContent='⏳ Regenerando...';
        const r=await fetch('/api/regenerar-diseno',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
        const d=await r.json(); if(d.error){document.getElementById('msg').textContent=d.error;return}
        token=d.token; mostrar(d.imagenes); document.getElementById('msg').textContent='';
      };
    }
    cargar();
  </script></body></html>`);
});

app.post('/api/crear-checkout', async (req,res) => {
  const {product_type,size,description,email} = req.body;
  const price = product_type==='hoodie'?3500:2500;
  try{
    const session = await stripe.checkout.sessions.create({
      payment_method_types:['card'], mode:'payment',
      line_items:[{price_data:{currency:'eur',product_data:{name:product_type==='hoodie'?'Sudadera personalizada':'Camiseta personalizada'},unit_amount:price},quantity:1}],
      metadata:{tipo:product_type, talla:size, descripcion:description, email},
      success_url:`${req.headers.origin}/exito?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url:`${req.headers.origin}/`
    });
    res.json({id:session.id});
  }catch(e){res.status(500).json({error:e.message})}
});

app.post('/api/generar-diseno', async (req,res) => {
  try{
    const session = await stripe.checkout.sessions.retrieve(req.body.session_id);
    const meta = session.metadata;
    const tkn = crypto.randomBytes(16).toString('hex');
    const p = await refinar(meta.descripcion);
    const imgs = await generar(p);
    pedidos.set(tkn, {imagenes:imgs, intentos:0, meta, sessionId:req.body.session_id});
    res.json({imagenes:imgs, token:tkn});
  }catch(e){res.status(500).json({error:e.message})}
});

app.post('/api/regenerar-diseno', async (req,res) => {
  const d = pedidos.get(req.body.token);
  if(!d) return res.status(404).json({error:'Token inválido'});
  d.intentos++;
  if(d.intentos>3) return res.status(429).json({error:'Máximo 3 regeneraciones. Elige un diseño actual.'});
  const p = await refinar(d.meta.descripcion);
  const imgs = await generar(p);
  d.imagenes = imgs;
  res.json({imagenes:imgs, token:req.body.token});
});

app.post('/api/confirmar-diseno', async (req,res) => {
  const d = pedidos.get(req.body.token);
  if(!d) return res.status(404).json({error:'Token inválido'});
  const url = d.imagenes[req.body.indice];
  const meta = d.meta;
  const vid = VARIANTES[meta.tipo][meta.talla];
  if(!vid) return res.status(400).json({error:'Talla no disponible. Configura los variant IDs en el código.'});
  const fid = await subir(url);
  const oid = await orden(vid, fid, meta.email, `ped_${Date.now()}`);
  await mailer.sendMail({
    from:`GuancheWear <${process.env.SMTP_USER}>`,
    to:meta.email,
    subject:`✅ Pedido #${oid} confirmado`,
    html:`<h2>¡Gracias por tu compra!</h2><p>Tu diseño único ha sido enviado a producción.</p><p><strong>Número de orden:</strong> ${oid}</p><p>Recibirás el paquete en 2‑4 días laborables.</p>`
  });
  pedidos.delete(req.body.token);
  res.json({mensaje:'✅ Diseño confirmado. Recibirás un email con el seguimiento.'});
});

app.listen(process.env.PORT||3000);