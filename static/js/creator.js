// Creator Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generateForm');
    const previewEmpty = document.getElementById('preview-empty-state');
    const previewText = document.getElementById('preview-text');
    const previewImage = document.getElementById('preview-image');
    const actionButtons = document.getElementById('post-actions');
    const generateBtn = form.querySelector('button[type="submit"]');

    let currentPostData = null;
    
    // Sync Preview with Active Account
    async function syncPreviewAccount() {
        try {
            const user = await API.getCurrentUser();
            if (user && user.active_account) {
                const acc = user.active_account;
                const nameEl = document.getElementById('preview-name');
                const avatarEl = document.getElementById('preview-avatar');
                const headlineEl = document.getElementById('preview-headline');
                
                if (nameEl) nameEl.textContent = acc.name;
                if (avatarEl) avatarEl.src = acc.profile_picture_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(acc.name)}&background=0a66c2&color=fff`;
                
                if (headlineEl) {
                    if (acc.linkedin_id && acc.linkedin_id.includes(':organization:')) {
                        headlineEl.textContent = 'Company Page';
                    } else {
                        headlineEl.textContent = 'AI & Machine Learning Enthusiast';
                    }
                }
            }
        } catch (e) {
            console.error('Failed to sync preview account:', e);
        }
    }
    
    syncPreviewAccount();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const topic = document.getElementById('topic').value.trim();
        if(!topic) {
            showToast('Please enter a topic', 'error');
            return;
        }

        // Setup loading state
        const originalBtnHTML = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        generateBtn.disabled = true;

        try {
            const tone = document.getElementById('tone').value;
            const length = document.getElementById('length').value;
            const imageStyle = document.getElementById('imageStyle').value;

            const result = await API.generateContent(topic, tone, length, imageStyle);

            if (!result || !result.text) {
                throw new Error('No content returned from AI. Please try again.');
            }

            // Update preview text
            previewText.textContent = result.text;

            // Update preview image
            const imageWrap = document.getElementById('preview-image-wrap');
            if (result.image_url) {
                previewImage.src = result.image_url;
                previewImage.onerror = () => { if (imageWrap) imageWrap.style.display = 'none'; };
                previewImage.onload = () => { if (imageWrap) imageWrap.style.display = ''; };
                if (imageWrap) imageWrap.style.display = '';
            } else {
                if (imageWrap) imageWrap.style.display = 'none';
            }

            // Show the preview and action buttons
            previewEmpty.classList.add('hidden');
            actionButtons.classList.remove('hidden');

            // Store current data for posting
            currentPostData = {
                topic: topic,
                generated_text: result.text,
                generated_image_url: result.image_url || null,
                tone: tone,
                length: length,
                image_style: imageStyle
            };

            showToast('Content generated successfully!');
            
        } catch (error) {
            console.error(error);
            showToast(error.message || 'Failed to generate content', 'error');
        } finally {
            generateBtn.innerHTML = originalBtnHTML;
            generateBtn.disabled = false;
        }
    });

    // Handle Post Now
    const postNowBtn = actionButtons.querySelector('button:last-child');
    postNowBtn.addEventListener('click', async () => {
        if (!currentPostData) return;

        const originalBtnHTML = postNowBtn.innerHTML;
        postNowBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Posting...';
        postNowBtn.disabled = true;

        try {
            // 1. Create the post in DB
            const postResponse = await API.createPost({
                ...currentPostData,
                status: 'Draft'
            });

            // 2. Publish it
            await API.publishPost(postResponse.post_id);

            showToast('Post published successfully to LinkedIn!');
            
            // Redirect to dashboard after a short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);

        } catch (error) {
            console.error(error);
            showToast(error.message || 'Failed to post to LinkedIn', 'error');
        } finally {
            postNowBtn.innerHTML = originalBtnHTML;
            postNowBtn.disabled = false;
        }
    });

    // Handle Schedule — use a native datetime-local picker (no manual parsing)
    const scheduleBtn = actionButtons.querySelector('button:first-child');
    scheduleBtn.addEventListener('click', () => {
        if (!currentPostData) return;

        // Build modal if it doesn't exist yet
        let modal = document.getElementById('scheduleModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'scheduleModal';
            modal.style.cssText = `
                position:fixed;inset:0;background:rgba(0,0,0,0.55);
                display:flex;align-items:center;justify-content:center;z-index:9999;
            `;
            modal.innerHTML = `
                <div style="background:#fff;border-radius:16px;padding:32px 28px;width:340px;
                            box-shadow:0 20px 60px rgba(0,0,0,0.25);font-family:inherit;">
                    <h3 style="margin:0 0 6px;font-size:18px;color:#1a1a2e;">📅 Schedule Post</h3>
                    <p style="margin:0 0 20px;font-size:13px;color:#666;">Pick a date and time to publish.</p>
                    <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:6px;">Date &amp; Time</label>
                    <input type="datetime-local" id="scheduleDatetimePicker"
                        style="width:100%;padding:10px 12px;border:1.5px solid #ddd;border-radius:8px;
                               font-size:14px;color:#333;outline:none;box-sizing:border-box;margin-bottom:20px;" />
                    <div style="display:flex;gap:10px;">
                        <button id="scheduleConfirmBtn"
                            style="flex:1;padding:11px;background:#0a66c2;color:#fff;border:none;
                                   border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
                            Schedule
                        </button>
                        <button id="scheduleCancelBtn"
                            style="flex:1;padding:11px;background:#f0f0f0;color:#333;border:none;
                                   border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
                            Cancel
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            document.getElementById('scheduleCancelBtn').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.style.display = 'none';
            });
        }

        // Pre-fill with current time + 1 hour
        const now = new Date(Date.now() + 60 * 60 * 1000);
        const localISO = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
            .toISOString().slice(0, 16);
        document.getElementById('scheduleDatetimePicker').value = localISO;
        modal.style.display = 'flex';

        // Confirm handler (replace each time to avoid duplicate listeners)
        const confirmBtn = document.getElementById('scheduleConfirmBtn');
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        newConfirmBtn.addEventListener('click', async () => {
            const picker = document.getElementById('scheduleDatetimePicker');
            if (!picker.value) {
                showToast('Please pick a date and time', 'error');
                return;
            }

            const scheduledDate = new Date(picker.value);
            if (isNaN(scheduledDate.getTime())) {
                showToast('Invalid date selected', 'error');
                return;
            }

            modal.style.display = 'none';
            newConfirmBtn.disabled = true;

            try {
                await API.createPost({
                    ...currentPostData,
                    status: 'Scheduled',
                    scheduled_time: scheduledDate.toISOString()
                });
                showToast('Post scheduled successfully!');
                window.location.href = '/calendar';
            } catch (error) {
                console.error('Scheduling Error:', error);
                showToast(error.message || 'Failed to schedule post', 'error');
            } finally {
                newConfirmBtn.disabled = false;
            }
        });
    });
});
