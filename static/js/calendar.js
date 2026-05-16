// Master Calendar Interface Intelligence Layer
document.addEventListener('DOMContentLoaded', () => {
    console.log('--- Initializing Master Calendar ---');
    const calendarEl = document.getElementById('calendar');
    const editorPanel = document.getElementById('postEditorPanel');
    const editorForm = document.getElementById('editorForm');
    const quickAddInput = document.getElementById('quickAddInput');
    const contextMenu = document.getElementById('contextMenu');

    if (!calendarEl) return;

    let calendar;
    let selectedEvent = null;

    // --- Helpers ---
    const togglePanel = (panel, show) => {
        if (!panel) return;
        if (show) panel.classList.remove('translate-x-full');
        else panel.classList.add('translate-x-full');
    };

    const hideContextMenu = () => {
        if (contextMenu) contextMenu.classList.add('hidden');
        selectedEvent = null;
    };

    window.navCalendar = (direction) => {
        if (!calendar) return;
        if (direction === 'prev') calendar.prev();
        else if (direction === 'next') calendar.next();
        else calendar.today();
        updateTitle();
    };

    window.changeView = (view) => {
        if (!calendar) return;
        calendar.changeView(view);
        updateTitle();
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('bg-primary', 'text-white');
            btn.classList.add('text-slate-500');
            if (btn.getAttribute('onclick')?.includes(view)) {
                btn.classList.add('bg-primary', 'text-white');
                btn.classList.remove('text-slate-500');
            }
        });
    };

    const updateTitle = () => {
        const titleEl = document.getElementById('calendarTitle');
        if (titleEl && calendar) titleEl.innerText = calendar.view.title;
    };

    // --- NLP Parser (Basic client-side fallback) ---
    const parseQuickAdd = (input) => {
        const text = input.toLowerCase();
        let topic = input;
        let date = new Date();
        
        if (text.includes('about ')) {
            topic = input.split(/about /i)[1].split(/ on | at | next /i)[0];
        }

        const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        days.forEach((day, index) => {
            if (text.includes(day)) {
                const today = new Date().getDay();
                let diff = index - today;
                if (diff < 0) diff += 7;
                date.setDate(date.getDate() + diff);
            }
        });

        const timeMatch = text.match(/at (\d+)(?::(\d+))?\s*(am|pm)?/i);
        if (timeMatch) {
            let hours = parseInt(timeMatch[1]);
            const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
            const meridian = timeMatch[3]?.toLowerCase();
            if (meridian === 'pm' && hours < 12) hours += 12;
            if (meridian === 'am' && hours === 12) hours = 0;
            date.setHours(hours, minutes, 0, 0);
        } else {
            date.setHours(9, 0, 0, 0);
        }

        return { topic: topic.trim(), scheduled_time: date.toISOString() };
    };

    // --- Heatmap ---
    const updateHeatmap = (events) => {
        const counts = {};
        events.forEach(e => {
            if (!e.start) return;
            const dateStr = (typeof e.start === 'string') ? e.start : e.start.toISOString();
            const date = dateStr.split('T')[0];
            counts[date] = (counts[date] || 0) + 1;
        });

        setTimeout(() => {
            document.querySelectorAll('.fc-daygrid-day').forEach(el => {
                const date = el.dataset.date;
                const count = counts[date] || 0;
                el.classList.remove('bg-blue-50/30', 'bg-blue-100/40', 'bg-blue-200/40', 'bg-blue-300/40');
                if (count === 1) el.classList.add('bg-blue-50/30');
                else if (count === 2) el.classList.add('bg-blue-100/40');
                else if (count === 3) el.classList.add('bg-blue-200/40');
                else if (count > 3) el.classList.add('bg-blue-300/40');
            });
        }, 100);
    };

    // --- Calendar Init ---
    try {
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: false,
            editable: true,
            droppable: true,
            selectable: true,
            dayMaxEvents: true,
            height: 'auto',
            nowIndicator: true,
            
            viewDidMount: () => updateTitle(),
            datesSet: () => updateTitle(),

            eventSources: [
                {
                    id: 'posts',
                    url: '/api/schedule/calendar',
                    failure: () => {
                        if (typeof showToast === 'function') showToast('Failed to load calendar events', 'error');
                    }
                }
            ],

            eventSourceSuccess: (content, response) => {
                if (response && response.url && response.url.includes('calendar')) {
                    updateHeatmap(content);
                }
                return content;
            },

            select: (info) => {
                hideContextMenu();
                openEditor({
                    topic: '',
                    text: '',
                    status: 'Draft',
                    scheduled_time: info.startStr.includes('T') ? info.startStr : info.startStr + 'T09:00:00'
                });
            },

            eventContent: (arg) => {
                const status = arg.event.extendedProps.status || 'Draft';
                const type = arg.event.extendedProps.type || 'post';
                const isSuggestion = type === 'suggestion';
                
                const icon = status === 'Published' ? 'fa-check-double' : 
                            status === 'Scheduled' ? 'fa-clock' : 
                            status === 'Pending Approval' ? 'fa-hourglass-half' :
                            isSuggestion ? 'fa-wand-magic-sparkles' : 'fa-pen-to-square';
                
                const bgColor = isSuggestion ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-200' : 
                               status === 'Published' ? 'bg-emerald-50 dark:bg-emerald-900/20' : '';

                return {
                    html: `<div class="p-1 px-2 flex items-center gap-1.5 overflow-hidden w-full rounded ${bgColor} ${status === 'Draft' ? 'opacity-80 border-l-2 border-dashed border-blue-400' : ''}">
                            <i class="fa-solid ${icon} text-[10px] ${isSuggestion ? 'text-purple-500' : ''}"></i>
                            <div class="text-[10px] font-semibold truncate flex-1">${arg.event.title}</div>
                          </div>`
                };
            },

            eventClick: (info) => {
                info.jsEvent.preventDefault();
                hideContextMenu();

                if (info.event.extendedProps.type === 'suggestion') {
                    openEditor({
                        topic: info.event.title.replace('\u2728 Suggestion: ', ''),
                        text: '',
                        status: 'Draft',
                        scheduled_time: info.event.start.toISOString()
                    });
                    return;
                }

                // Fetch full post data from API and show preview modal
                openPostPreview(info.event.id, info.event);
            },

            eventDrop: async (info) => {
                hideContextMenu();
                if (info.event.extendedProps.type === 'suggestion') {
                    info.revert();
                    return;
                }
                await updatePost(info.event.id, { scheduled_time: info.event.start.toISOString() });
                if (typeof showToast === 'function') showToast('Post rescheduled successfully', 'success');
            },

            eventDidMount: (info) => {
                info.el.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    if (info.event.extendedProps.type === 'suggestion') return;
                    
                    selectedEvent = info.event;
                    let x = e.clientX;
                    let y = e.clientY;
                    
                    const menuWidth = 192;
                    const menuHeight = 120;
                    if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 10;
                    if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 10;
                    
                    contextMenu.style.left = x + 'px';
                    contextMenu.style.top = y + 'px';
                    contextMenu.classList.remove('hidden');
                });
            },

            dateClick: () => hideContextMenu()
        });

        calendar.render();
    } catch (e) {
        console.error('Calendar Init Error:', e);
        if (typeof showToast === 'function') showToast('Calendar failed to initialize', 'error');
    }

    // --- Context Menu Actions ---
    window.handleContextAction = async (action) => {
        if (!selectedEvent) return;
        
        const eventId = selectedEvent.id;

        if (action === 'delete') {
            if (confirm('Delete this post?')) {
                try {
                    await fetch('/api/posts/' + eventId, { method: 'DELETE' });
                    selectedEvent.remove();
                    if (typeof showToast === 'function') showToast('Post deleted', 'success');
                } catch (error) {
                    if (typeof showToast === 'function') showToast('Failed to delete post', 'error');
                }
            }
        } else if (action === 'rewrite') {
            if (typeof showToast === 'function') showToast('AI Rewrite feature coming in next update!', 'info');
        } else if (action === 'adjust') {
            if (typeof showToast === 'function') showToast('Tone adjustment feature coming in next update!', 'info');
        }
        
        hideContextMenu();
    };

    document.addEventListener('click', (e) => {
        if (contextMenu && !contextMenu.contains(e.target)) hideContextMenu();
    });

    // --- Editor Logic ---
    // Helper: convert UTC ISO string from server → local datetime string for <input type="datetime-local">
    const utcToLocalInputValue = (utcStr) => {
        if (!utcStr) return '';
        const d = new Date(utcStr);          // browser interprets Z as UTC, converts to local
        const pad = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    // Helper: convert datetime-local string → ISO 8601 WITH local timezone offset
    // e.g. "2026-05-10T07:27" → "2026-05-10T07:27:00+05:30"
    // This ensures the backend _to_utc_naive() correctly converts to UTC.
    const localTimeToISO = (datetimeLocalStr) => {
        if (!datetimeLocalStr) return '';
        const d = new Date(datetimeLocalStr);  // parsed as local time by browser
        return d.toISOString();                 // toISOString() always returns UTC (Z), which _to_utc_naive handles correctly
    };

    const openEditor = (post) => {
        document.getElementById('editorPostId').value = post.id || '';
        document.getElementById('editorTopic').value = post.topic || '';
        document.getElementById('editorContent').value = post.text || '';
        document.getElementById('editorStatus').value = post.status || 'Draft';
        document.getElementById('editorTime').value = utcToLocalInputValue(post.scheduled_time);
        
        updateCharCount();
        togglePanel(editorPanel, true);
    };

    // Character counter
    const updateCharCount = () => {
        const content = document.getElementById('editorContent');
        const count = content ? content.value.length : 0;
        const counter = document.getElementById('charCount');
        if (counter) counter.textContent = count + ' / 3000';
    };

    document.getElementById('editorContent')?.addEventListener('input', updateCharCount);

    // Close editor button
    document.getElementById('closeEditor')?.addEventListener('click', () => {
        togglePanel(editorPanel, false);
    });

    // Placeholder insertion
    window.insertPlaceholder = (placeholder) => {
        const textarea = document.getElementById('editorContent');
        if (!textarea) return;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;
        textarea.value = text.substring(0, start) + placeholder + text.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + placeholder.length;
        textarea.focus();
        updateCharCount();
    };

    editorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('editorPostId').value;

        // Convert datetime-local value (naive local time) → UTC ISO string
        // so the backend stores UTC and the scheduler comparison works correctly
        const rawTime = document.getElementById('editorTime').value;
        const scheduledTimeUTC = rawTime ? localTimeToISO(rawTime) : '';

        const data = {
            topic: document.getElementById('editorTopic').value || 'Untitled',
            generated_text: document.getElementById('editorContent').value,
            status: document.getElementById('editorStatus').value,
            scheduled_time: scheduledTimeUTC
        };

        try {
            if (id) {
                await updatePost(id, data);
                if (typeof showToast === 'function') showToast('Post updated successfully', 'success');
            } else {
                await createPost(data);
                if (typeof showToast === 'function') showToast('Post created successfully', 'success');
            }
            togglePanel(editorPanel, false);
            calendar.refetchEvents();
        } catch (error) {
            if (typeof showToast === 'function') showToast('Failed to save post', 'error');
        }
    });

    const createPost = async (data) => {
        const response = await fetch('/api/posts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to create post');
        return response.json();
    };

    const updatePost = async (id, data) => {
        const response = await fetch('/api/posts/' + id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update post');
        return response.json();
    };

    window.deletePost = async () => {
        const id = document.getElementById('editorPostId').value;
        if (!id) {
            togglePanel(editorPanel, false);
            return;
        }
        if (confirm('Delete this post?')) {
            try {
                await fetch('/api/posts/' + id, { method: 'DELETE' });
                togglePanel(editorPanel, false);
                calendar.refetchEvents();
                if (typeof showToast === 'function') showToast('Post deleted', 'success');
            } catch (error) {
                if (typeof showToast === 'function') showToast('Failed to delete post', 'error');
            }
        }
    };

    // --- AI Rewrite Button ---
    document.getElementById('aiRewriteBtn')?.addEventListener('click', async () => {
        const topic = document.getElementById('editorTopic').value;
        const content = document.getElementById('editorContent').value;
        if (!topic && !content) {
            if (typeof showToast === 'function') showToast('Enter a topic or content first', 'error');
            return;
        }
        if (typeof showToast === 'function') showToast('AI optimization coming in next update!', 'info');
    });

    // ========================================================
    // POST PREVIEW MODAL
    // ========================================================
    let previewPostId = null; // track which post is being previewed
    let previewPostData = null; // cache the full post data

    const statusBadgeClasses = {
        'Published':  'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
        'Scheduled':  'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        'Draft':      'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
        'Failed':     'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
        'Pending Approval': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    };

    const statusIcons = {
        'Published':  'fa-check-double',
        'Scheduled':  'fa-clock',
        'Draft':      'fa-pen-to-square',
        'Failed':     'fa-triangle-exclamation',
        'Pending Approval': 'fa-hourglass-half',
    };

    const openPostPreview = async (postId, calendarEvent) => {
        previewPostId = postId;
        const modal = document.getElementById('postPreviewModal');
        if (!modal) return;

        // Show modal immediately with topic from calendar (fast)
        const status = calendarEvent?.extendedProps?.status || 'Draft';
        document.getElementById('previewTopic').textContent = calendarEvent ? calendarEvent.title : 'Loading...';
        document.getElementById('previewText').textContent = 'Loading post content…';
        document.getElementById('previewImageWrap').classList.add('hidden');

        const badge = document.getElementById('previewStatusBadge');
        badge.className = `inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${statusBadgeClasses[status] || statusBadgeClasses['Draft']}`;
        badge.innerHTML = `<i class="fa-solid ${statusIcons[status] || 'fa-pen-to-square'}"></i> ${status}`;

        const publishBtn = document.getElementById('previewPublishBtn');
        publishBtn.style.display = status === 'Published' ? 'none' : '';

        modal.classList.remove('hidden');
        modal.classList.add('flex');

        // Fetch full post data via the single-post endpoint
        try {
            const res = await fetch(`/api/posts/${postId}`);
            if (!res.ok) throw new Error('Could not load post');
            const post = await res.json();
            populatePreview(post);
        } catch (err) {
            console.error('Preview fetch error:', err);
            // Fallback: use whatever data the calendar event has
            populatePreview({
                id: postId,
                topic: calendarEvent?.title || 'Untitled',
                text: calendarEvent?.extendedProps?.text || '',
                image_url: calendarEvent?.extendedProps?.image_url || '',
                status: status,
                scheduled_time: calendarEvent?.start?.toISOString() || null
            });
        }
    };

    const populatePreview = (post) => {
        previewPostData = post;

        document.getElementById('previewTopic').textContent = post.topic || 'Untitled';
        document.getElementById('previewText').textContent = post.text || post.generated_text || '(No content)';

        // Scheduled time
        const timeEl = document.getElementById('previewTime');
        if (post.scheduled_time) {
            const d = new Date(post.scheduled_time);
            timeEl.textContent = d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
        } else {
            timeEl.textContent = 'No scheduled time';
        }

        // Image
        const imageUrl = post.image_url || post.generated_image_url || '';
        const imageWrap = document.getElementById('previewImageWrap');
        const imageEl = document.getElementById('previewImage');
        if (imageUrl) {
            imageEl.src = imageUrl;
            imageWrap.classList.remove('hidden');
        } else {
            imageWrap.classList.add('hidden');
        }

        // Status badge
        const status = post.status || 'Draft';
        const badge = document.getElementById('previewStatusBadge');
        const iconClass = statusIcons[status] || 'fa-pen-to-square';
        badge.className = `inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${statusBadgeClasses[status] || statusBadgeClasses['Draft']}`;
        badge.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${status}`;

        const publishBtn = document.getElementById('previewPublishBtn');
        if (status === 'Published') {
            publishBtn.style.display = 'none';
        } else {
            publishBtn.style.display = '';
        }
    };

    window.closePostPreview = () => {
        const modal = document.getElementById('postPreviewModal');
        if (!modal) return;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        previewPostId = null;
        previewPostData = null;
    };

    // Edit button: close modal, open editor panel with full data
    document.getElementById('previewEditBtn')?.addEventListener('click', () => {
        if (!previewPostData && !previewPostId) return;
        closePostPreview();
        const data = previewPostData || {};
        openEditor({
            id: previewPostId,
            topic: data.topic || '',
            text: data.text || data.generated_text || '',
            status: data.status || 'Draft',
            scheduled_time: data.scheduled_time || ''
        });
    });

    // Delete button
    document.getElementById('previewDeleteBtn')?.addEventListener('click', async () => {
        if (!previewPostId) return;
        if (!confirm('Delete this post?')) return;
        try {
            await fetch('/api/posts/' + previewPostId, { method: 'DELETE' });
            closePostPreview();
            calendar.refetchEvents();
            if (typeof showToast === 'function') showToast('Post deleted', 'success');
        } catch (err) {
            if (typeof showToast === 'function') showToast('Failed to delete post', 'error');
        }
    });

    // Publish Now button
    document.getElementById('previewPublishBtn')?.addEventListener('click', async () => {
        if (!previewPostId) return;
        const btn = document.getElementById('previewPublishBtn');
        const origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Publishing...';
        try {
            const res = await fetch('/api/posts/' + previewPostId + '/publish', { method: 'POST' });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Publish failed');
            closePostPreview();
            calendar.refetchEvents();
            if (typeof showToast === 'function') showToast('Post published to LinkedIn! ✓', 'success');
        } catch (err) {
            if (typeof showToast === 'function') showToast(err.message || 'Failed to publish', 'error');
            btn.innerHTML = origHtml;
            btn.disabled = false;
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closePostPreview();
    });

    // --- Quick Add with NLP ---
    document.getElementById('quickAddBtn').addEventListener('click', async () => {
        const val = quickAddInput.value.trim();
        if (!val) return;

        const btn = document.getElementById('quickAddBtn');
        btn.disabled = true;
        btn.textContent = 'Generating...';

        try {
            // Step 1: Parse NLP to extract topic + scheduled_time
            const nlpResponse = await fetch('/api/schedule/parse-nlp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: val })
            });

            let parsed;
            if (nlpResponse.ok) {
                parsed = await nlpResponse.json();
            } else {
                parsed = parseQuickAdd(val);
            }

            // Step 2: Generate real AI content (text + image) for the topic
            if (typeof showToast === 'function') showToast('Generating AI content…', 'info');
            const genResponse = await fetch('/api/posts/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: parsed.topic, tone: 'Professional', length: 'Medium', imageStyle: 'Professional' })
            });

            let generatedText = parsed.topic;   // fallback: bare topic
            let generatedImageUrl = null;

            if (genResponse.ok) {
                const genData = await genResponse.json();
                generatedText    = genData.text      || parsed.topic;
                generatedImageUrl = genData.image_url || null;
            }

            // Step 3: Create the scheduled post with full AI content
            await createPost({
                topic:                parsed.topic,
                generated_text:       generatedText,
                generated_image_url:  generatedImageUrl,
                scheduled_time:       parsed.scheduled_time,
                status:               'Scheduled'
            });

            quickAddInput.value = '';
            calendar.refetchEvents();
            if (typeof showToast === 'function') showToast('Post scheduled with AI content!', 'success');
        } catch (error) {
            console.error('Quick add failed:', error);
            if (typeof showToast === 'function') showToast('Failed to schedule post', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Add to Calendar';
        }
    });

    quickAddInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('quickAddBtn').click();
        }
    });

    window.handleAICommand = async (cmd) => {
        try {
            let body = {};
            if (cmd === 'theme-week') {
                const topic = prompt('Enter a theme topic for the week (e.g. Artificial Intelligence):');
                if (topic === null) return; // user cancelled
                body = { topic: topic.trim() || 'Artificial Intelligence' };
            }

            const response = await fetch('/api/schedule/ai/' + cmd, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('Command failed');
            const result = await response.json();
            calendar.refetchEvents();
            const count = result.count ? ` (${result.count} posts added)` : '';
            if (typeof showToast === 'function') showToast(`Done!${count}`, 'success');
        } catch (error) {
            console.error('AI command error:', error);
            if (typeof showToast === 'function') showToast('Could not complete. Please try again.', 'info');
        }
    };

    // --- Ideas Bin with Drag & Drop ---
    const fetchIdeas = async () => {
        try {
            const res = await fetch('/api/schedule/ideas');
            if (!res.ok) throw new Error('Failed to fetch ideas');
            const ideas = await res.json();
            
            const container = document.getElementById('ideasContainer');
            if (!container) return;
            
            let html = '';
            ideas.forEach(i => {
                html += '<div class="idea-item p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl mb-2 text-sm cursor-move hover:shadow-md transition-all group" draggable="true" data-id="' + i.id + '" data-content="' + i.content.replace(/"/g, '"') + '"><div class="flex items-start justify-between gap-2"><span class="flex-1">' + i.content + '</span><button onclick="deleteIdea(' + i.id + ')" class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-all"><i class="fa-solid fa-xmark"></i></button></div>';
            });
            html += '<button onclick="addIdea()" class="w-full p-2 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-400 hover:text-primary hover:border-primary transition-all"><i class="fa-solid fa-plus"></i> New Idea</button>';
            
            container.innerHTML = html;
            
            container.querySelectorAll('.idea-item').forEach(item => {
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', item.dataset.content);
                    e.dataTransfer.setData('idea-id', item.dataset.id);
                    e.dataTransfer.effectAllowed = 'copy';
                    item.classList.add('opacity-50');
                });
                item.addEventListener('dragend', () => {
                    item.classList.remove('opacity-50');
                });
            });
        } catch (error) {
            console.error('Failed to fetch ideas:', error);
        }
    };

    window.addIdea = async () => {
        const content = prompt('Enter idea:');
        if (content && content.trim()) {
            try {
                await fetch('/api/schedule/ideas', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content.trim() })
                });
                fetchIdeas();
                if (typeof showToast === 'function') showToast('Idea saved!', 'success');
            } catch (error) {
                if (typeof showToast === 'function') showToast('Failed to save idea', 'error');
            }
        }
    };

    window.deleteIdea = async (id) => {
        if (!confirm('Delete this idea?')) return;
        try {
            await fetch('/api/schedule/ideas/' + id, { method: 'DELETE' });
            fetchIdeas();
            if (typeof showToast === 'function') showToast('Idea deleted', 'success');
        } catch (error) {
            if (typeof showToast === 'function') showToast('Failed to delete idea', 'error');
        }
    };

    // Handle external drops (ideas dropped on calendar)
    calendarEl.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });

    calendarEl.addEventListener('drop', async (e) => {
        e.preventDefault();
        const content = e.dataTransfer.getData('text/plain');
        if (!content) return;
        
        const dropDate = new Date();
        dropDate.setHours(9, 0, 0, 0);
        
        try {
            await createPost({
                topic: content.substring(0, 50),
                generated_text: content,
                status: 'Draft',
                scheduled_time: dropDate.toISOString()
            });
            calendar.refetchEvents();
            if (typeof showToast === 'function') showToast('Idea scheduled!', 'success');
        } catch (error) {
            if (typeof showToast === 'function') showToast('Failed to schedule idea', 'error');
        }
    });

    // --- Sidebar Toggle ---
    document.getElementById('toggleIdeas')?.addEventListener('click', () => {
        const sidebar = document.getElementById('ideasBin');
        if (sidebar) {
            sidebar.classList.toggle('w-64');
            sidebar.classList.toggle('w-0');
            sidebar.classList.toggle('opacity-0');
        }
    });

    // Initialize
    fetchIdeas();
});
