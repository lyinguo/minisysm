import fs from 'fs'
import path from 'path'

function walk(dir) {
  const files = []
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    if (fs.statSync(full).isDirectory()) files.push(...walk(full))
    else if (name.endsWith('.vue')) files.push(full)
  }
  return files
}

const replacements = [
  [/'制单.{0,3}: /g, "'制单人': "],
  [/'属.{0,3}: /g, "'属性': "],
  [/'折扣.{0,3}: /g, "'折扣额': "],
  [/'增加应收.{0,3}: /g, "'增加应收款': "],
  [/'增加预收.{0,3}: /g, "'增加预收款': "],
  [/'增加应付.{0,3}: /g, "'增加应付款': "],
  [/'增加预付.{0,3}: /g, "'增加预付款': "],
  [/'应收款余.{0,3}: /g, "'应收款余额': "],
  [/'应付款余.{0,3}: /g, "'应付款余额': "],
  [/失.\)/g, "失败')"],
  [/失.\?/g, "失败'"],
]

for (const file of walk('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report')) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  for (const [re, rep] of replacements) s = s.replace(re, rep)
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}

console.log('all export keys done')
