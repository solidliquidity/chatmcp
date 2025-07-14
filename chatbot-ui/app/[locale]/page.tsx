"use client"

import { IconArrowRight } from "@tabler/icons-react"
import Image from "next/image"
import Link from "next/link"

export default function HomePage() {
  return (
    <div className="flex size-full flex-col items-center justify-center">
      <div>
        <Image 
          src="/pebble-logo.png" 
          alt="Pebble Logo" 
          width={80} 
          height={80}
          className="rounded-lg"
        />
      </div>

      <div className="mt-2 text-4xl font-bold">Pebble Finance</div>

      <Link
        className="mt-4 flex w-[200px] items-center justify-center rounded-md bg-blue-500 p-2 font-semibold"
        href="/login"
      >
        Start
        <IconArrowRight className="ml-1" size={20} />
      </Link>
    </div>
  )
}
