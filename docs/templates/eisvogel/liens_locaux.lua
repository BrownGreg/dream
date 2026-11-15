-- Filtre pandoc pour les PDF Eisvogel.
-- 1. Un lien vers un fichier du dépôt (chemin relatif, sans « http ») serait mort dans un PDF :
--    on garde son texte, sans le lien.
-- 2. Avec la métadonnée « saut-de-page-chapitres: true », chaque titre de niveau 1 (sauf le
--    premier) commence sur une nouvelle page.

local saut = false
local premier = true

function Meta(m)
  saut = m["saut-de-page-chapitres"] == true
end

function Link(el)
  if not el.target:match("^%a+:") and not el.target:match("^#") then
    return el.content
  end
end

function Header(el)
  if saut and el.level == 1 then
    if premier then
      premier = false
    else
      return { pandoc.RawBlock("latex", "\\clearpage"), el }
    end
  end
end

return { { Meta = Meta }, { Link = Link, Header = Header } }
