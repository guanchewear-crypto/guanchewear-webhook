const express = require('express');
const cors = require('cors');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const axios = require('axios');
const nodemailer = require('nodemailer');
const crypto = require('crypto');
const OpenAI = require('openai');

const app = express();
app.use(cors({ origin: process.env.CORS_ORIGIN || 'https://guanchewear.es' }));
app.use(express.json({ limit: '5mb' }));
app.use(express.static('public'));

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const mailer = nodemailer.createTransport({
  host: 'smtp.gmail.com', port: 587, secure: false,
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
});

// Almacenamiento temporal (en producción usar Vercel KV o similar)
const pedidos = new Map();

// ─── IDs de variantes de Printify (ACTUALIZAR con los reales) ───
const VARIANTES = {
  't-shirt': { S: '12126', M: '12125', L: '12124', XL: '12127', XXL: '12128' },
  'hoodie': { S: '32918', M: '32919', L: '32920', XL: '32921', XXL: '32922' }
};

// ─── Utilidades ───

function generarId() {
  return crypto.randomBytes(16).toString('hex');
}

// ─── GPT-4: Refinar prompt ───

async function refinarPrompt(descripcion) {
  const completion = await openai.chat.completions.create({
    model: 'gpt-4-turbo',
    messages: [
      {
        role: 'system',
        content: `Eres un diseñador textil experto. Convierte la idea del cliente en un prompt profesional para DALL-E 3.
        Reglas:
        - Traduce todo a inglés (DALL-E funciona mejor en inglés)
        - Añade detalles de calidad: "high quality, detailed, vector art, clean lines"
        - Especifica "transparent background" o "white background" según corresponda
        - Indica "suitable for t-shirt print, centered composition"
        - Máximo 300 caracteres
        - Devuelve SOLO el prompt, sin explicaciones`
      },
      { role: 'user', content: descripcion }
    ],
    max_tokens: 150,
    temperature: 0.7
  });
  return completion.choices[0].message.content;
}

// ─── DALL-E 3: Generar imágenes ───

async function generarImagenes(prompt, n = 2) {
  const response = await openai.images.generate({
    model: 'dall-e-3',
    prompt: prompt,
    n: n,
    size: '1024x1024',
    quality: 'standard',
    style: 'vivid'
  });
  return response.data.map(img => img.url);
}

// ─── Subir imagen a Printify ───

async function subirAPrintify(imageUrl) {
  const buf = (await axios.get(imageUrl, { responseType: 'arraybuffer' })).data;

  const uploadResp = await axios.post(
    'https://api.printify.com/v1/uploads.json',
    {},
    { headers: { Authorization: `Bearer ${process.env.PRINTIFY_API_KEY}` } }
  );
  const uploadUrl = uploadResp.data.upload_url;

  await axios.put(uploadUrl, buf, {
    headers: {
      Authorization: `Bearer ${process.env.PRINTIFY_API_KEY}`,
      'Content-Type': 'image/png'
    }
  });
  return uploadResp.data.id;
}

// ─── Crear orden en Printify ───

async function crearOrdenPrintify(variantId, fileId, email, externalId) {
  const shopsResp = await axios.get('https://api.printify.com/v1/shops.json', {
    headers: { Authorization: `Bearer ${process.env.PRINTIFY_API_KEY}` }
  });
  const shopId = shopsResp.data[0].id;

  const orderResp = await axios.post(
    `https://api.printify.com/v1/shops/${shopId}/orders.json`,
    {
      external_id: externalId,
      label: `GuancheWear - ${externalId}`,
      line_items: [{
        variant_id: variantId,
        quantity: 1,
        files: [{
          id: fileId,
          placement: 'front',
          position: { x: 0.5, y: 0.5, scale: 1, angle: 0 }
        }]
      }],
      recipient: { name: 'Cliente', email: email },
      address: {
        first_name: 'Cliente',
        last_name: '',
        email: email,
        country: 'ES',
        region: '',
        address1: 'Dirección pendiente',
        city: 'Ciudad pendiente',
        zip: '00000',
        phone: ''
      },
      shipping_method: 1
    },
    { headers: { Authorization: `Bearer ${process.env.PRINTIFY_API_KEY}`, 'Content-Type': 'application/json' } }
  );
  return orderResp.data.id;
}

// ─── Servir frontend ───

app.get('/', (req, res) => {
  res.sendFile(__dirname + '/public/index.html');
});

// ─── Página de diseño (post-pago) ───

app.get('/diseno', (req, res) => {
  res.sendFile(__dirname + '/public/diseno.html');
});

// ─── API: Crear diseño (SIN pago) ───

app.post('/api/crear-diseno', async (req, res) => {
  try {
    const { product_type, size, color, description } = req.body;

    if (!product_type || !size || !description) {
      return res.status(400).json({ error: 'Faltan campos requeridos' });
    }

    const token = generarId();
    const prompt = await refinarPrompt(description);
    const imagenes = await generarImagenes(prompt);

    pedidos.set(token, {
      imagenes,
      intentos: 0,
      maxIntentos: 3,
      prompt,
      product_type,
      size,
      color,
      createdAt: Date.now()
    });

    console.log(`✅ Diseño generado: ${token} (${product_type}/${size})`);

    res.json({
      token,
      imagenes,
      prompt,
      regeneraciones_restantes: 3
    });
  } catch (error) {
    console.error('Error al generar diseño:', error.message);
    res.status(500).json({ error: 'Error al generar el diseño: ' + error.message });
  }
});

// ─── API: Regenerar diseño ───

app.post('/api/regenerar-diseno', async (req, res) => {
  try {
    const { token, description } = req.body;
    const pedido = pedidos.get(token);

    if (!pedido) {
      return res.status(404).json({ error: 'Sesión de diseño no encontrada' });
    }

    pedido.intentos++;
    if (pedido.intentos > pedido.maxIntentos) {
      return res.status(429).json({
        error: 'Máximo 3 regeneraciones alcanzado. Confirma el diseño actual.',
        regeneraciones_restantes: 0
      });
    }

    const prompt = description
      ? await refinarPrompt(description)
      : pedido.prompt;

    const imagenes = await generarImagenes(prompt);
    pedido.imagenes = imagenes;
    pedido.prompt = prompt;

    res.json({
      token,
      imagenes,
      prompt,
      regeneraciones_restantes: pedido.maxIntentos - pedido.intentos
    });
  } catch (error) {
    console.error('Error al regenerar:', error.message);
    res.status(500).json({ error: 'Error al regenerar: ' + error.message });
  }
});

// ─── API: Crear checkout (después de confirmar diseño) ───

app.post('/api/crear-checkout', async (req, res) => {
  try {
    const { token, designIndex } = req.body;
    const pedido = pedidos.get(token);

    if (!pedido) {
      return res.status(404).json({ error: 'Sesión de diseño no encontrada. El diseño puede haber expirado.' });
    }

    const imagenElegida = pedido.imagenes[designIndex];
    if (!imagenElegida) {
      return res.status(400).json({ error: 'Índice de diseño inválido' });
    }

    const price = pedido.product_type === 'hoodie' ? 3500 : 2500;
    const nombre = pedido.product_type === 'hoodie' ? 'Sudadera personalizada' : 'Camiseta personalizada';

    // Guardar la imagen seleccionada
    pedido.imagenConfirmada = imagenElegida;
    pedido.designIndex = designIndex;

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      mode: 'payment',
      line_items: [{
        price_data: {
          currency: 'eur',
          product_data: {
            name: nombre,
            description: `Diseño único generado por IA. Talla: ${pedido.size}. Pedido: ${token.slice(0, 8)}`,
            images: [imagenElegida]
          },
          unit_amount: price
        },
        quantity: 1
      }],
      metadata: {
        token: token,
        tipo: pedido.product_type,
        talla: pedido.size,
        color: pedido.color || '',
        imagen: imagenElegida
      },
      success_url: `${req.headers.origin}/exito?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${req.headers.origin}/diseno?token=${token}`
    });

    res.json({ id: session.id, url: session.url });
  } catch (error) {
    console.error('Error al crear checkout:', error.message);
    res.status(500).json({ error: 'Error al crear el pago: ' + error.message });
  }
});

// ─── Webhook de Stripe (confirmación de pago) ───

app.post('/api/webhook-stripe', async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Error de firma webhook:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    const token = session.metadata.token;
    const pedido = pedidos.get(token);

    if (!pedido) {
      console.error(`Pedido no encontrado para token: ${token}`);
      return res.status(200).json({ received: true });
    }

    try {
      const imagenUrl = pedido.imagenConfirmada || pedido.imagenes[0];
      const variantId = VARIANTES[pedido.product_type]?.[pedido.size];

      if (!variantId) {
        console.error(`Variant ID no encontrado para ${pedido.product_type}/${pedido.size}`);
        await mailer.sendMail({
          from: `GuancheWear <${process.env.SMTP_USER}>`,
          to: session.customer_details.email,
          subject: '⚠️ Necesitamos tu dirección',
          html: `<h2>¡Gracias por tu compra!</h2>
                 <p>Tu diseño está listo. Necesitamos que nos respondas este email con tu dirección de envío para procesar el pedido.</p>
                 <p><strong>Token de diseño:</strong> ${token}</p>`
        });
        return res.json({ received: true });
      }

      const fileId = await subirAPrintify(imagenUrl);
      const orderId = await crearOrdenPrintify(variantId, fileId, session.customer_details.email, `GW-${token.slice(0, 8)}`);

      await mailer.sendMail({
        from: `GuancheWear <${process.env.SMTP_USER}>`,
        to: session.customer_details.email,
        subject: `✅ Pedido confirmado - #GW${token.slice(0, 8)}`,
        html: `
          <div style="font-family:Arial;max-width:600px;margin:0 auto;">
            <h1 style="color:#D4A853;">¡Gracias por tu compra! 🎉</h1>
            <p>Tu diseño único ha sido enviado a producción.</p>
            <div style="text-align:center;margin:20px 0;">
              <img src="${imagenUrl}" alt="Tu diseño" style="max-width:300px;border-radius:8px;border:2px solid #D4A853;">
            </div>
            <p><strong>Número de pedido:</strong> GW${token.slice(0, 8)}</p>
            <p><strong>Producto:</strong> ${pedido.product_type === 'hoodie' ? 'Sudadera' : 'Camiseta'} - Talla ${pedido.size}</p>
            <p>Recibirás otro email con el número de seguimiento cuando se envíe.</p>
            <hr style="border:1px solid #eee;">
            <p style="color:#888;font-size:12px;">GuancheWear - Tu diseño único creado por IA</p>
          </div>`
      });

      pedidos.delete(token);
      console.log(`✅ Pedido completado: GW${token.slice(0, 8)}`);
    } catch (error) {
      console.error('Error al procesar pedido:', error.message);
      // Notificar al admin
      await mailer.sendMail({
        from: `GuancheWear <${process.env.SMTP_USER}>`,
        to: process.env.SMTP_USER,
        subject: '⚠️ Error en pedido - requiere intervención manual',
        html: `<p>Error procesando pedido ${token}: ${error.message}</p>`
      });
    }
  }

  res.json({ received: true });
});

// ─── API: Estado del diseño ───

app.get('/api/estado-diseno', async (req, res) => {
  const { token, session_id } = req.query;

  if (token) {
    const pedido = pedidos.get(token);
    if (!pedido) return res.json({ valido: false });
    return res.json({
      valido: true,
      product_type: pedido.product_type,
      size: pedido.size,
      regeneraciones_restantes: pedido.maxIntentos - pedido.intentos
    });
  }

  if (session_id) {
    try {
      const session = await stripe.checkout.sessions.retrieve(session_id);
      res.json({
        valido: true,
        pagado: session.payment_status === 'paid',
        email: session.customer_details?.email,
        metadata: session.metadata
      });
    } catch {
      res.json({ valido: false });
    }
    return;
  }

  res.json({ error: 'Se requiere token o session_id' });
});

// ─── Página de éxito ───

app.get('/exito', (req, res) => {
  res.send(`<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>🎉 Pedido confirmado - GuancheWear</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:Inter,system-ui,sans-serif;background:#0A0A0A;color:#F5F5F5;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px}
    .card{background:#1A1A1A;border-radius:24px;padding:40px;max-width:500px;width:100%;text-align:center;border:1px solid #333}
    h1{color:#D4A853;font-size:2rem;margin-bottom:10px}
    .icon{font-size:4rem;margin-bottom:20px}
    .status{color:#888;margin-bottom:20px}
    .email-note{background:#242424;border-radius:12px;padding:15px;margin:20px 0;font-size:0.9rem;color:#aaa}
    .check{display:inline-block;width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#D4A853,#E8C06A);margin-bottom:20px;position:relative}
    .check::after{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-60%) rotate(-45deg);width:30px;height:15px;border-left:4px solid #0A0A0A;border-bottom:4px solid #0A0A0A}
    .footer{color:#555;font-size:0.8rem;margin-top:20px}
  </style>
</head>
<body>
  <div class="card">
    <div class="check"></div>
    <h1>¡Pedido confirmado!</h1>
    <p class="status">Tu diseño único está en producción. Recibirás un email con el seguimiento en 2-4 días.</p>
    <div class="email-note">📬 Te hemos enviado un email con los detalles de tu pedido.</div>
    <p style="color:#888;font-size:0.9rem">¿Tienes dudas? Escríbenos a guanchewear@gmail.com</p>
    <div class="footer">GuancheWear — Tu diseño, tu esencia</div>
  </div>
</body>
</html>`);
});

// ─── Cleanup de sesiones expiradas (cada hora) ───
setInterval(() => {
  const now = Date.now();
  for (const [token, pedido] of pedidos.entries()) {
    if (now - pedido.createdAt > 3600000) { // 1 hora
      pedidos.delete(token);
    }
  }
}, 3600000);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 GuancheWear webhook corriendo en puerto ${PORT}`);
});

module.exports = app;