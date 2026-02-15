function hexToRgbObject(hex) {
  if (!hex || typeof hex !== "string") return null
  const normalized = hex.trim().replace("#", "")
  const full = normalized.length === 3
    ? normalized.split("").map((c) => c + c).join("")
    : normalized
  if (!/^[0-9a-fA-F]{6}$/.test(full)) return null
  const n = parseInt(full, 16)
  return {
    r: ((n >> 16) & 255) / 255,
    g: ((n >> 8) & 255) / 255,
    b: (n & 255) / 255
  }
}

function parsePadding(value) {
  if (!value) return null
  if (typeof value === "number") {
    return { top: value, right: value, bottom: value, left: value }
  }
  const parts = String(value).split(",").map((x) => Number(x.trim()))
  if (parts.length === 1 && Number.isFinite(parts[0])) {
    return { top: parts[0], right: parts[0], bottom: parts[0], left: parts[0] }
  }
  if (parts.length === 4 && parts.every(Number.isFinite)) {
    return { top: parts[0], right: parts[1], bottom: parts[2], left: parts[3] }
  }
  return null
}

function readFiniteNumber(value) {
  if (value === null || value === undefined || value === "") return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

async function getNodeById(id) {
  if (!id) return null
  return figma.getNodeByIdAsync(id)
}

async function appendToParent(node, parentId) {
  if (parentId) {
    const parent = await getNodeById(parentId)
    if (parent && "appendChild" in parent) {
      parent.appendChild(node)
      return
    }
  }
  figma.currentPage.appendChild(node)
}

function setFill(node, fill) {
  if (!fill || !("fills" in node)) return
  const rgb = hexToRgbObject(fill)
  if (!rgb) return
  node.fills = [{ type: "SOLID", color: rgb }]
}

function serializeNode(node) {
  return {
    id: node.id,
    name: node.name,
    type: node.type
  }
}

async function handleCommand(command, args) {
  switch (command) {
    case "status":
      return {
        fileName: figma.root.name,
        fileKey: typeof figma.fileKey === "string" ? figma.fileKey : "",
        pageId: figma.currentPage.id,
        pageName: figma.currentPage.name
      }

    case "create-page": {
      const page = figma.createPage()
      page.name = args.name || "Untitled"
      return serializeNode(page)
    }

    case "set-current-page": {
      const idOrName = args.idOrName
      if (!idOrName) throw new Error("Missing idOrName")
      let page = figma.root.children.find((p) => p.id === idOrName || p.name === idOrName)
      if (!page) throw new Error(`Page not found: ${idOrName}`)
      figma.currentPage = page
      return serializeNode(page)
    }

    case "create-frame": {
      const frame = figma.createFrame()
      frame.name = args.name || "Frame"
      frame.x = Number(args.x || 0)
      frame.y = Number(args.y || 0)
      frame.resize(Number(args.width || 100), Number(args.height || 100))
      setFill(frame, args.fill)
      if (args.stroke) {
        const rgb = hexToRgbObject(args.stroke)
        if (rgb) frame.strokes = [{ type: "SOLID", color: rgb }]
      }
      const strokeWeight = readFiniteNumber(args.strokeWeight)
      if (strokeWeight !== null) {
        frame.strokeWeight = strokeWeight
      }
      const radius = readFiniteNumber(args.radius)
      if (radius !== null) {
        frame.cornerRadius = radius
      }
      const opacity = readFiniteNumber(args.opacity)
      if (opacity !== null) {
        frame.opacity = opacity
      }
      if (args.layoutMode && args.layoutMode !== "NONE") {
        frame.layoutMode = args.layoutMode
        frame.primaryAxisSizingMode = "AUTO"
        frame.counterAxisSizingMode = "AUTO"
        const itemSpacing = readFiniteNumber(args.itemSpacing)
        if (itemSpacing !== null) {
          frame.itemSpacing = itemSpacing
        }
        const padding = parsePadding(args.padding)
        if (padding) {
          frame.paddingTop = padding.top
          frame.paddingRight = padding.right
          frame.paddingBottom = padding.bottom
          frame.paddingLeft = padding.left
        }
      }
      await appendToParent(frame, args.parentId)
      return serializeNode(frame)
    }

    case "create-text": {
      const textNode = figma.createText()
      const family = args.fontFamily || "Inter"
      const style = args.fontStyle || "Regular"
      await figma.loadFontAsync({ family, style })
      textNode.fontName = { family, style }
      textNode.characters = args.text || ""
      textNode.name = args.name || "Text"
      textNode.x = Number(args.x || 0)
      textNode.y = Number(args.y || 0)
      const fontSize = readFiniteNumber(args.fontSize)
      if (fontSize !== null) {
        textNode.fontSize = fontSize
      }
      setFill(textNode, args.fill)
      const opacity = readFiniteNumber(args.opacity)
      if (opacity !== null) {
        textNode.opacity = opacity
      }
      await appendToParent(textNode, args.parentId)
      return serializeNode(textNode)
    }

    case "set-text": {
      const node = await getNodeById(args.id)
      if (!node || node.type !== "TEXT") throw new Error("Text node not found")
      if (typeof args.text !== "string") throw new Error("Missing text")
      if (node.fontName && typeof node.fontName === "object") {
        await figma.loadFontAsync({ family: node.fontName.family, style: node.fontName.style })
      } else {
        await figma.loadFontAsync({ family: "Inter", style: "Regular" })
      }
      node.characters = args.text
      return serializeNode(node)
    }

    case "set-fill": {
      const node = await getNodeById(args.id)
      if (!node) throw new Error("Node not found")
      setFill(node, args.color)
      return serializeNode(node)
    }

    case "set-opacity": {
      const node = await getNodeById(args.id)
      if (!node || !("opacity" in node)) throw new Error("Opacity-capable node not found")
      const value = readFiniteNumber(args.value)
      if (value === null) throw new Error("Missing opacity value")
      node.opacity = value
      return serializeNode(node)
    }

    case "set-layout": {
      const node = await getNodeById(args.id)
      if (!node || !("layoutMode" in node)) throw new Error("Layout node not found")
      if (args.mode) node.layoutMode = args.mode
      const gap = readFiniteNumber(args.gap)
      if (gap !== null) node.itemSpacing = gap
      const padding = parsePadding(args.padding)
      if (padding) {
        node.paddingTop = padding.top
        node.paddingRight = padding.right
        node.paddingBottom = padding.bottom
        node.paddingLeft = padding.left
      }
      return serializeNode(node)
    }

    default:
      throw new Error(`Unsupported command: ${command}`)
  }
}

figma.showUI(__html__, { width: 320, height: 120, visible: false })

figma.ui.onmessage = async (msg) => {
  const id = msg && msg.id ? msg.id : "unknown"
  const command = msg ? msg.command : ""
  const args = msg && msg.args ? msg.args : {}

  try {
    const result = await handleCommand(command, args)
    figma.ui.postMessage({ id, ok: true, result })
  } catch (error) {
    figma.ui.postMessage({
      id,
      ok: false,
      error: error && error.message ? error.message : String(error)
    })
  }
}
