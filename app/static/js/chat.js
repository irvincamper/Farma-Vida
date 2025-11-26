function startChatPolling(otherId, meId) {
  const box = document.getElementById('chat-box');
  if (!box) return;

  async function fetchMessages() {
    try {
      const res = await fetch(`/chat/api/conversation/${otherId}`);
      if (!res.ok) return;
      const data = await res.json();
      renderMessages(data.messages || []);
    } catch (e) {
      console.error('Error fetching messages', e);
    }
  }

  function renderMessages(messages) {
    box.innerHTML = '';
    for (const m of messages) {
      const isMe = (m.sender_id === meId);
      const wrapper = document.createElement('div');
      wrapper.style.marginBottom = '8px';
      wrapper.style.textAlign = isMe ? 'right' : 'left';

      const bubble = document.createElement('div');
      bubble.style.display = 'inline-block';
      bubble.style.maxWidth = '75%';
      bubble.style.padding = '8px';
      bubble.style.borderRadius = '8px';
      bubble.style.background = isMe ? '#d1ffd6' : '#fff';
      bubble.style.border = '1px solid #eee';
      bubble.textContent = m.content || '';

      const time = document.createElement('div');
      time.style.fontSize = '0.8em';
      time.style.color = '#666';
      time.textContent = m.created_at || '';

      wrapper.appendChild(bubble);
      wrapper.appendChild(time);
      box.appendChild(wrapper);
    }
    // scroll to bottom
    box.scrollTop = box.scrollHeight;
  }

  // send message via AJAX when form submitted
  const form = document.getElementById('send-form');
  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const input = document.getElementById('message-input');
      if (!input) return;
      const content = input.value.trim();
      if (!content) return;
      try {
        const payload = { receiver_id: otherId, content };
        const res = await fetch('/chat/api/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          input.value = '';
          await fetchMessages();
        }
      } catch (err) {
        console.error('Error sending message', err);
      }
    });
  }

  // initial fetch and interval
  fetchMessages();
  const poller = setInterval(fetchMessages, 3000);

  // Optional: Supabase Realtime (activates only if window.SUPABASE_URL and window.SUPABASE_ANON_KEY are present)
  if (window.SUPABASE_URL && window.SUPABASE_ANON_KEY) {
    // load supabase-js from CDN if not already loaded
    (async function initRealtime() {
      if (!window.supabase) {
        await new Promise((resolve, reject) => {
          const s = document.createElement('script');
          s.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/dist/umd/supabase.min.js';
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        }).catch(err => { console.warn('No se pudo cargar supabase-js:', err); });
      }

      try {
        const supabaseClient = window.supabase || supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
        // Suscribirse a inserciones en la tabla 'mensajes' donde receiver_id = meId OR sender_id = meId (para ver ambos lados)
        const channel = supabaseClient
          .channel('public:mensajes')
          .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'mensajes' }, payload => {
            const newRow = payload.new || payload.record || payload;
            if (!newRow) return;
            // Si el mensaje pertenece a esta conversación, refrescar
            const belongs = (newRow.sender_id === otherId && newRow.receiver_id === meId) || (newRow.sender_id === meId && newRow.receiver_id === otherId);
            if (belongs) {
              // append quickly
              appendMessage(newRow, meId, box);
            }
          })
          .subscribe();

        function appendMessage(m, meIdLocal, boxEl) {
          const isMe = (m.sender_id === meIdLocal);
          const wrapper = document.createElement('div');
          wrapper.style.marginBottom = '8px';
          wrapper.style.textAlign = isMe ? 'right' : 'left';
          const bubble = document.createElement('div');
          bubble.style.display = 'inline-block';
          bubble.style.maxWidth = '75%';
          bubble.style.padding = '8px';
          bubble.style.borderRadius = '8px';
          bubble.style.background = isMe ? '#d1ffd6' : '#fff';
          bubble.style.border = '1px solid #eee';
          bubble.textContent = m.content || '';
          const time = document.createElement('div');
          time.style.fontSize = '0.8em';
          time.style.color = '#666';
          time.textContent = m.created_at || '';
          wrapper.appendChild(bubble);
          wrapper.appendChild(time);
          boxEl.appendChild(wrapper);
          boxEl.scrollTop = boxEl.scrollHeight;
        }
      } catch (err) {
        console.warn('Realtime init error', err);
      }
    })();
  }
}
