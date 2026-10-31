(function(){
 var slides=[].slice.call(document.querySelectorAll('.slide')),i=0,deck=document.querySelector('.deck');
 function fit(){var s=Math.min(innerWidth/1280,innerHeight/720);deck.style.transform='scale('+s+')';}
 function show(n){i=Math.max(0,Math.min(slides.length-1,n));slides.forEach(function(s,k){s.classList.toggle('on',k===i)});
  var notes=document.getElementById('notes-live');if(notes)notes.innerHTML=slides[i].querySelector('.notes').innerHTML;
  if(location.hash!=='#'+(i+1))history.replaceState(null,'','#'+(i+1));}
 addEventListener('resize',fit);
 addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' ')show(i+1);
  else if(e.key==='ArrowLeft'||e.key==='PageUp')show(i-1);
  else if(e.key==='Home')show(0);else if(e.key==='End')show(slides.length-1);
  else if(e.key==='n')document.body.classList.toggle('shownotes');});
 addEventListener('click',function(e){if(e.target.closest('a'))return;show(e.clientX>innerWidth/2?i+1:i-1);});
 fit();show((parseInt(location.hash.slice(1),10)||1)-1);
})();
