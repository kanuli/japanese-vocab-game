/* Repro: Japanese IME after final n (ねっしん -> 熱心).
 * Native candidate selection cannot be synthesized in headless Chrome;
 * check the critical invariant: the site's input listener NEVER changes
 * input.value or selection while the OS IME is composing. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const handlers={};let activeTimers=new Map(),tid=0;
function node(){
  return {children:[],className:'',textContent:'',parentNode:{insertBefore(){}},
    classList:{toggle(){}},setAttribute(){},addEventListener(type,cb){this.on??={};this.on[type]=cb;},
    appendChild(x){this.children.push(x);},focus(){}};
}
const input=node();
input.value='';
input.addEventListener=function(type,cb){(handlers[type]??=[]).push(cb);};
input.dispatchEvent=function(ev){
  ev.stopImmediatePropagation??=function(){};
  for(const cb of (handlers[ev.type]||[]))cb(ev);
};
const clearState={};
const context={window:{},document:{
  getElementById:k=>k==='search'?input:null,
  createElement:()=>node(),
  querySelector:()=>null
},Event:function(type){this.type=type;},
  setTimeout(cb){const id=++tid;activeTimers.set(id,cb);return id;},
  clearTimeout(id){activeTimers.delete(id);}};
vm.runInNewContext(fs.readFileSync('wordlist-japanese-input.js','utf8'),context);
function emit(type,options={}){
  input.dispatchEvent({type,isComposing:!!options.isComposing,
    inputType:options.inputType||'insertText',stopImmediatePropagation(){}});
}
const search=context.window.WordlistJapaneseSearch;
assert.ok(search,'query-only Romaji search helper missing');
assert.equal(search.toHiragana('nesshin'),'ねっしん');
assert.equal(search.toHiragana('tenjinsama'),'てんじんさま');
assert.equal(search.toHiragana('kanji'),'かんじ');
assert.equal(search.toHiragana('n'),'ん');
assert.equal(search.toHiragana('na'),'な');
input.value='n';
emit('input');
assert.equal(input.value,'n','romaji typed into native IME must stay unmodified');
emit('compositionstart');
input.value='ねっし';
emit('input',{isComposing:true,inputType:'insertCompositionText'});
assert.equal(input.value,'ねっし');
input.value='ねっしん';
emit('input',{isComposing:true,inputType:'insertCompositionText'});
assert.equal(input.value,'ねっしん');
emit('compositionend');
input.value='熱心';
emit('input',{inputType:'insertFromComposition'});
assert.equal(input.value,'熱心','site must preserve confirmed Kanji candidate');
input.value='nesshin';
emit('input');
assert.equal(input.value,'nesshin','fallback Romaji search must not modify visible input');
console.log('JAPANESE IME SEARCH: PASS (native text preserved + query Romaji)');
