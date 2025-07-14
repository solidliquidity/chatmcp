"use client"

import Link from "next/link"
import Image from "next/image"
import { FC } from "react"

interface BrandProps {
  theme?: "dark" | "light"
}

export const Brand: FC<BrandProps> = ({ theme = "dark" }) => {
  return (
    <Link
      className="flex cursor-pointer flex-col items-center hover:opacity-50"
      href="https://www.chatbotui.com"
      target="_blank"
      rel="noopener noreferrer"
    >
      <div className="mb-2">
        <Image 
          src="/pebble-logo.png" 
          alt="Pebble Logo" 
          width={60} 
          height={60}
          className="rounded-lg"
        />
      </div>

      <div className="text-4xl font-bold tracking-wide">Pebble Finance</div>
    </Link>
  )
}
